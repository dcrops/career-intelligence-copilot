"""Employer-need coverage selection for M4 cover-letter positioning.

Deterministic and inspectable. Not a numeric optimiser.

Default: two evidence sources. A third is allowed only when it covers a
high-priority DIRECT or RELATED need that the first two do not already
represent. Sources need not be projects.
"""

from __future__ import annotations

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.document_positioning.catalogue import (
    identities_mentioned_in_text,
    normalise_label,
    resolve_identity,
    supporting_identities,
)
from career_intelligence.document_positioning.models import (
    ClassifiedNeed,
    PositioningPlan,
    SupportStatus,
    TrajectoryMode,
)
from career_intelligence.document_positioning.policies import (
    _is_data_engineering_role,
    _is_testing_role,
)
from career_intelligence.profile.models import (
    CareerProfile,
    Certification,
    ExperienceEntry,
    Project,
)

DEFAULT_SOURCE_COUNT = 2
MAX_SOURCE_COUNT = 3
HIGH_PRIORITY_LIMIT = 4

_UNRANKED = 999

_TYPE_TIEBREAK = {
    "trajectory": 0,
    "project": 1,
    "employment": 2,
    "independent_engineering": 3,
    "certification": 4,
    "professional_development": 5,
    "methodology": 6,
}


class EvidenceSourceCandidate:
    """A truthful CareerProfile source that may cover employer needs."""

    def __init__(
        self,
        *,
        source_id: str,
        source_type: str,
        name: str,
        organisation: str | None,
        identities: frozenset[str],
        labels: tuple[str, ...],
        facts: tuple[str, ...],
        technologies: tuple[str, ...],
        portfolio_match_rank: int | None,
        chapter: str | None,
    ) -> None:
        self.source_id = source_id
        self.source_type = source_type
        self.name = name
        self.organisation = organisation
        self.identities = identities
        self.labels = labels
        self.facts = facts
        self.technologies = technologies
        self.portfolio_match_rank = portfolio_match_rank
        self.chapter = chapter
        self.label_norms = frozenset(normalise_label(item) for item in labels if item)


class SelectedEvidenceSource:
    def __init__(
        self,
        candidate: EvidenceSourceCandidate,
        *,
        purpose: str,
        employer_needs_covered: tuple[str, ...],
        coverage_kinds: tuple[str, ...],
        override_reason: str | None,
    ) -> None:
        self.source_id = candidate.source_id
        self.source_type = candidate.source_type
        self.name = candidate.name
        self.organisation = candidate.organisation
        self.identities = candidate.identities
        self.labels = candidate.labels
        self.facts = candidate.facts
        self.technologies = candidate.technologies
        self.labels = candidate.labels
        self.portfolio_match_rank = candidate.portfolio_match_rank
        self.chapter = candidate.chapter
        self.purpose = purpose
        self.employer_needs_covered = employer_needs_covered
        self.coverage_kinds = coverage_kinds
        self.override_reason = override_reason


class PortfolioMatchOverride:
    def __init__(
        self,
        *,
        project_id: str,
        project_name: str,
        portfolio_match_rank: int,
        reason: str,
    ) -> None:
        self.project_id = project_id
        self.project_name = project_name
        self.portfolio_match_rank = portfolio_match_rank
        self.reason = reason


class EvidenceSelection:
    def __init__(
        self,
        *,
        sources: tuple[SelectedEvidenceSource, ...],
        overrides: tuple[PortfolioMatchOverride, ...],
        high_priority_needs: tuple[str, ...],
    ) -> None:
        self.sources = sources
        self.overrides = overrides
        self.high_priority_needs = high_priority_needs
        self.default_count = DEFAULT_SOURCE_COUNT
        self.max_count = MAX_SOURCE_COUNT


def select_cover_letter_evidence(
    profile: CareerProfile,
    positioning: PositioningPlan,
    *,
    strategy: ApplicationStrategy | None = None,
) -> EvidenceSelection:
    """Select a bounded set of evidence sources by employer-need coverage."""
    ranks = _portfolio_ranks(strategy)
    actionable = _actionable_needs(positioning)
    high_priority = tuple(_high_priority_needs(actionable))
    candidates = _collect_candidates(
        profile,
        positioning.trajectory_mode,
        ranks,
    )
    selected: list[SelectedEvidenceSource] = []
    covered: set[int] = set()

    if positioning.trajectory_mode == "full_chapters":
        trajectory = next(
            (item for item in candidates if item.source_type == "trajectory"),
            None,
        )
        if trajectory is not None:
            picked = _select_one(
                trajectory,
                high_priority,
                covered,
                purpose=(
                    "Career trajectory is the hiring argument "
                    f"({positioning.trajectory_mode}); portfolio evidence supports "
                    "it rather than replacing it."
                ),
            )
            selected.append(picked)
            covered.update(_covered_ranks(trajectory, high_priority))

    while len(selected) < DEFAULT_SOURCE_COUNT:
        remaining = [need for need in high_priority if need.need.rank not in covered]
        pick = _best_candidate(
            candidates,
            selected,
            remaining or list(actionable),
            prefer_uncovered=bool(remaining),
            trajectory_mode=positioning.trajectory_mode,
        )
        if pick is None:
            pick = _fallback_candidate(candidates, selected, profile)
        if pick is None:
            break
        remaining_for_purpose = remaining or list(actionable)
        covered_needs, kinds = _coverage_labels(pick, remaining_for_purpose or high_priority)
        if not covered_needs:
            covered_needs, kinds = _coverage_labels(pick, actionable)
        purpose = _purpose_for(pick, covered_needs, kinds, third=False)
        selected.append(
            _select_one(pick, high_priority, covered, purpose=purpose)
        )
        covered.update(_covered_ranks(pick, high_priority))
        if positioning.trajectory_mode == "bridge" and len(selected) == 1 and len(selected) < DEFAULT_SOURCE_COUNT:
            transfer = _bridge_transfer_candidate(candidates, selected)
            if transfer is not None:
                t_needs, t_kinds = _coverage_labels(transfer, actionable)
                selected.append(
                    _select_one(
                        transfer,
                        high_priority,
                        covered,
                        purpose=(
                            "Trajectory mode is bridge: include one prior "
                            "engineering/testing/data employment source as a "
                            "transfer argument, not as a second AI project."
                        ),
                    )
                )
                covered.update(_covered_ranks(transfer, high_priority))
                _ = (t_needs, t_kinds)

    remaining_high = [need for need in high_priority if need.need.rank not in covered]
    if len(selected) == DEFAULT_SOURCE_COUNT and remaining_high:
        third = _best_candidate(
            candidates,
            selected,
            remaining_high,
            prefer_uncovered=True,
            trajectory_mode=positioning.trajectory_mode,
        )
        if third is not None and _covered_ranks(third, remaining_high):
            covered_needs, kinds = _coverage_labels(third, remaining_high)
            selected.append(
                _select_one(
                    third,
                    high_priority,
                    covered,
                    purpose=(
                        "Third source allowed: covers remaining high-priority "
                        f"need(s) {', '.join(covered_needs)} not already "
                        "represented by the first two sources."
                    ),
                )
            )
            covered.update(_covered_ranks(third, high_priority))

    while len(selected) < DEFAULT_SOURCE_COUNT:
        pick = _fallback_candidate(candidates, selected, profile)
        if pick is None:
            break
        selected.append(
            _select_one(
                pick,
                high_priority,
                covered,
                purpose=(
                    "Fallback truthful AI Engineering evidence; no remaining "
                    "DIRECT/RELATED employer-need overlap."
                ),
            )
        )

    overrides = _portfolio_overrides(candidates, selected, ranks, high_priority)
    _apply_override_reasons(selected, overrides)
    return EvidenceSelection(
        sources=tuple(selected[:MAX_SOURCE_COUNT]),
        overrides=tuple(overrides),
        high_priority_needs=tuple(item.need.label for item in high_priority),
    )


def coverage_kind_for(
    candidate: EvidenceSourceCandidate,
    need: ClassifiedNeed,
) -> str | None:
    """Return 'direct' or 'related' if this source may support the need."""
    status = need.classification.status
    if status is SupportStatus.UNSUPPORTED:
        return None
    if status is SupportStatus.SUPPORTED_DIRECT:
        target = (
            need.classification.promotable_identity
            or need.classification.requested_identity
        )
        if target and candidate.identities & supporting_identities(target):
            return "direct"
        if _label_hit(candidate, need):
            return "direct"
        return None
    if status is SupportStatus.SUPPORTED_RELATED:
        promo = need.classification.promotable_identity
        if promo and promo in candidate.identities:
            return "related"
        label = need.classification.promotable_profile_label
        if label and normalise_label(label) in candidate.label_norms:
            return "related"
        return None
    return None


def _actionable_needs(positioning: PositioningPlan) -> list[ClassifiedNeed]:
    return [
        item
        for item in positioning.employer_needs
        if item.classification.status
        in {SupportStatus.SUPPORTED_DIRECT, SupportStatus.SUPPORTED_RELATED}
    ]


def _high_priority_needs(actionable: list[ClassifiedNeed]) -> list[ClassifiedNeed]:
    """DIRECT needs first, plus early RELATED needs that can justify coverage.

    RELATED needs after rank 3 do not force a third source or displace AI
    evidence. Rank-1 RELATED (for example AWS Bedrock) remains high-priority.
    """
    selected: list[ClassifiedNeed] = []
    for item in actionable:
        status = item.classification.status
        if status is SupportStatus.SUPPORTED_DIRECT:
            selected.append(item)
        elif (
            status is SupportStatus.SUPPORTED_RELATED
            and item.need.rank <= 3
        ):
            selected.append(item)
        if len(selected) >= HIGH_PRIORITY_LIMIT:
            break
    return selected


def _portfolio_ranks(strategy: ApplicationStrategy | None) -> dict[str, int]:
    if strategy is None:
        return {}
    ranks: dict[str, int] = {}
    for item in strategy.portfolio_emphasis:
        rank = item.source_rank
        if rank is None:
            continue
        ranks[item.project_id] = rank
    if ranks:
        return ranks
    for index, item in enumerate(strategy.portfolio_emphasis, start=1):
        ranks[item.project_id] = index
    return ranks


def _collect_candidates(
    profile: CareerProfile,
    trajectory_mode: TrajectoryMode,
    ranks: dict[str, int],
) -> list[EvidenceSourceCandidate]:
    candidates: list[EvidenceSourceCandidate] = []
    for project in profile.projects:
        candidates.append(_project_candidate(project, ranks.get(project.id)))
    for entry in profile.experience:
        packed = _experience_candidate(entry, trajectory_mode)
        if packed is not None:
            candidates.append(packed)
    for cert in profile.certifications:
        packed = _cert_candidate(cert)
        if packed is not None:
            candidates.append(packed)
    if trajectory_mode in {"full_chapters", "bridge"}:
        candidates.append(_trajectory_candidate(profile, trajectory_mode))
    return candidates


def _project_candidate(project: Project, rank: int | None) -> EvidenceSourceCandidate:
    labels = tuple([*project.technologies, *project.demonstrates])
    blobs = [project.name, project.summary, *labels, *project.outcomes]
    facts = tuple(
        item
        for item in (
            project.summary,
            *project.outcomes[:2],
            *project.demonstrates[:3],
        )
        if item.strip()
    )
    return EvidenceSourceCandidate(
        source_id=f"project:{project.id}",
        source_type="project",
        name=project.name,
        organisation=None,
        identities=_identities_from(blobs, labels),
        labels=labels,
        facts=facts,
        technologies=tuple(project.technologies),
        portfolio_match_rank=rank,
        chapter=None,
    )


def _experience_candidate(
    entry: ExperienceEntry,
    trajectory_mode: TrajectoryMode,
) -> EvidenceSourceCandidate | None:
    if entry.kind == "independent_engineering":
        source_type = "independent_engineering"
        chapter = "independent_ai"
    elif entry.kind == "professional_development":
        source_type = "professional_development"
        chapter = "study"
    elif entry.kind == "employment":
        source_type = "employment"
        if _is_testing_role(entry):
            chapter = "testing"
            if trajectory_mode == "ai_lead":
                return None
        elif _is_data_engineering_role(entry):
            chapter = "data_engineering"
        else:
            chapter = "other_commercial"
    else:
        return None
    labels = tuple(entry.technologies)
    blobs = [entry.title, entry.organisation, *entry.highlights, *labels]
    facts = tuple(
        item
        for item in (
            f"{entry.title} at {entry.organisation}.",
            *entry.highlights[:3],
        )
        if item.strip()
    )
    return EvidenceSourceCandidate(
        source_id=f"experience:{entry.id}",
        source_type=source_type,
        name=f"{entry.title} — {entry.organisation}",
        organisation=entry.organisation,
        identities=_identities_from(blobs, labels),
        labels=labels,
        facts=facts,
        technologies=tuple(entry.technologies),
        portfolio_match_rank=None,
        chapter=chapter,
    )


def _cert_candidate(cert: Certification) -> EvidenceSourceCandidate | None:
    identity = resolve_identity(cert.name)
    mentioned = identities_mentioned_in_text(cert.name)
    identities = set(mentioned)
    if identity:
        identities.add(identity)
    if not identities:
        return None
    return EvidenceSourceCandidate(
        source_id=f"certification:{cert.id}",
        source_type="certification",
        name=cert.name,
        organisation=cert.issuer,
        identities=frozenset(identities),
        labels=(cert.name,),
        facts=(cert.name,),
        technologies=(),
        portfolio_match_rank=None,
        chapter=None,
    )


def _trajectory_candidate(
    profile: CareerProfile,
    trajectory_mode: TrajectoryMode,
) -> EvidenceSourceCandidate:
    testing = next(
        (entry for entry in profile.experience if _is_testing_role(entry)),
        None,
    )
    de = next(
        (entry for entry in profile.experience if _is_data_engineering_role(entry)),
        None,
    )
    independent = next(
        (
            entry
            for entry in profile.experience
            if entry.kind == "independent_engineering"
        ),
        None,
    )
    facts: list[str] = []
    orgs: list[str] = []
    if testing:
        facts.append(
            f"Commercial software testing/automation as {testing.title} at "
            f"{testing.organisation}."
        )
        orgs.append(testing.organisation)
    if de:
        facts.append(
            f"Commercial data engineering as {de.title} at {de.organisation}."
        )
        orgs.append(de.organisation)
    if independent:
        facts.append(
            f"Current independent AI Engineering as {independent.title} at "
            f"{independent.organisation}."
        )
        orgs.append(independent.organisation)
    labels = tuple(orgs)
    return EvidenceSourceCandidate(
        source_id="trajectory:career-chapters",
        source_type="trajectory",
        name="QA → data engineering → AI Engineering trajectory",
        organisation=None,
        identities=frozenset(),
        labels=labels,
        facts=tuple(facts),
        technologies=(),
        portfolio_match_rank=None,
        chapter=trajectory_mode,
    )


def _identities_from(blobs: list[str], labels: tuple[str, ...]) -> frozenset[str]:
    found: set[str] = set()
    for label in labels:
        resolved = resolve_identity(label)
        if resolved:
            found.add(resolved)
    for blob in blobs:
        found.update(identities_mentioned_in_text(blob))
    return frozenset(found)


def _label_hit(candidate: EvidenceSourceCandidate, need: ClassifiedNeed) -> bool:
    needles = [need.need.label]
    if need.classification.promotable_profile_label:
        needles.append(need.classification.promotable_profile_label)
    return any(normalise_label(item) in candidate.label_norms for item in needles)


def _covered_ranks(
    candidate: EvidenceSourceCandidate,
    needs: list[ClassifiedNeed] | tuple[ClassifiedNeed, ...],
) -> set[int]:
    return {
        need.need.rank
        for need in needs
        if coverage_kind_for(candidate, need) is not None
    }


def _coverage_labels(
    candidate: EvidenceSourceCandidate,
    needs: list[ClassifiedNeed] | tuple[ClassifiedNeed, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    labels: list[str] = []
    kinds: list[str] = []
    for need in needs:
        kind = coverage_kind_for(candidate, need)
        if kind is None:
            continue
        labels.append(need.need.label)
        kinds.append(kind)
    return tuple(labels), tuple(kinds)


def _already_selected(
    selected: list[SelectedEvidenceSource],
    candidate: EvidenceSourceCandidate,
) -> bool:
    return any(item.source_id == candidate.source_id for item in selected)


def _best_candidate(
    candidates: list[EvidenceSourceCandidate],
    selected: list[SelectedEvidenceSource],
    target_needs: list[ClassifiedNeed],
    *,
    prefer_uncovered: bool,
    trajectory_mode: TrajectoryMode,
) -> EvidenceSourceCandidate | None:
    _ = trajectory_mode
    usable = [
        item
        for item in candidates
        if not _already_selected(selected, item) and item.source_type != "trajectory"
    ]
    scored: list[tuple[tuple[int, int, int, int, str], EvidenceSourceCandidate]] = []
    for item in usable:
        direct = 0
        related = 0
        for need in target_needs:
            kind = coverage_kind_for(item, need)
            if kind == "direct":
                direct += 1
            elif kind == "related":
                related += 1
        if prefer_uncovered and direct == 0 and related == 0:
            continue
        rank = item.portfolio_match_rank if item.portfolio_match_rank is not None else _UNRANKED
        key = (
            -direct,
            -related,
            rank,
            _TYPE_TIEBREAK.get(item.source_type, 9),
            item.source_id,
        )
        scored.append((key, item))
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0])
    return scored[0][1]


def _bridge_transfer_candidate(
    candidates: list[EvidenceSourceCandidate],
    selected: list[SelectedEvidenceSource],
) -> EvidenceSourceCandidate | None:
    for item in candidates:
        if _already_selected(selected, item):
            continue
        if item.source_type == "employment" and item.chapter in {
            "testing",
            "data_engineering",
        }:
            return item
    return None


def _fallback_candidate(
    candidates: list[EvidenceSourceCandidate],
    selected: list[SelectedEvidenceSource],
    profile: CareerProfile,
) -> EvidenceSourceCandidate | None:
    _ = profile
    preferred_types = ("project", "independent_engineering")
    unused = [
        item
        for item in candidates
        if not _already_selected(selected, item) and item.source_type in preferred_types
    ]
    unused.sort(
        key=lambda item: (
            _TYPE_TIEBREAK.get(item.source_type, 9),
            item.portfolio_match_rank if item.portfolio_match_rank is not None else _UNRANKED,
            item.source_id,
        )
    )
    return unused[0] if unused else None


def _purpose_for(
    candidate: EvidenceSourceCandidate,
    covered_needs: tuple[str, ...],
    kinds: tuple[str, ...],
    *,
    third: bool,
) -> str:
    _ = third
    if not covered_needs:
        return (
            f"Selected as truthful {candidate.source_type.replace('_', ' ')} "
            "evidence when remaining employer needs were unsupported or already "
            "covered."
        )
    kind_note = ", ".join(
        f"{label} ({kind})" for label, kind in zip(covered_needs, kinds, strict=False)
    )
    rank = candidate.portfolio_match_rank
    rank_note = (
        f" PortfolioMatch rank {rank}." if rank is not None else ""
    )
    return (
        f"Selected because this {candidate.source_type.replace('_', ' ')} covers "
        f"{kind_note}.{rank_note}"
    )


def _select_one(
    candidate: EvidenceSourceCandidate,
    high_priority: tuple[ClassifiedNeed, ...] | list[ClassifiedNeed],
    covered: set[int],
    *,
    purpose: str,
) -> SelectedEvidenceSource:
    needs, kinds = _coverage_labels(candidate, high_priority)
    if not needs:
        needs, kinds = _coverage_labels(candidate, list(high_priority))
    _ = covered
    return SelectedEvidenceSource(
        candidate,
        purpose=purpose,
        employer_needs_covered=needs,
        coverage_kinds=kinds,
        override_reason=None,
    )


def _portfolio_overrides(
    candidates: list[EvidenceSourceCandidate],
    selected: list[SelectedEvidenceSource],
    ranks: dict[str, int],
    high_priority: tuple[ClassifiedNeed, ...] | list[ClassifiedNeed],
) -> list[PortfolioMatchOverride]:
    if not ranks:
        return []
    selected_ids = {item.source_id for item in selected}
    overrides: list[PortfolioMatchOverride] = []
    ranked_projects = sorted(
        (
            item
            for item in candidates
            if item.source_type == "project" and item.portfolio_match_rank is not None
        ),
        key=lambda item: item.portfolio_match_rank or _UNRANKED,
    )
    for item in ranked_projects:
        if item.source_id in selected_ids:
            continue
        if (item.portfolio_match_rank or _UNRANKED) > 2:
            continue
        reason = _override_reason(item, selected, high_priority)
        overrides.append(
            PortfolioMatchOverride(
                project_id=item.source_id.removeprefix("project:"),
                project_name=item.name,
                portfolio_match_rank=item.portfolio_match_rank or 0,
                reason=reason,
            )
        )
    return overrides


def _override_reason(
    dropped: EvidenceSourceCandidate,
    selected: list[SelectedEvidenceSource],
    high_priority: tuple[ClassifiedNeed, ...] | list[ClassifiedNeed],
) -> str:
    dropped_needs, _kinds = _coverage_labels(dropped, high_priority)
    chosen = ", ".join(
        f"{item.name} ({', '.join(item.employer_needs_covered) or 'no remaining need overlap'})"
        for item in selected
    )
    if dropped_needs:
        return (
            f"PortfolioMatch rank {dropped.portfolio_match_rank} project "
            f"'{dropped.name}' was not selected. PositioningPlan need coverage "
            f"preferred {chosen} over this project's overlap "
            f"({', '.join(dropped_needs)})."
        )
    return (
        f"PortfolioMatch rank {dropped.portfolio_match_rank} project "
        f"'{dropped.name}' was not selected because it does not cover remaining "
        f"high-priority employer needs. Selected instead: {chosen}."
    )


def _apply_override_reasons(
    selected: list[SelectedEvidenceSource],
    overrides: list[PortfolioMatchOverride],
) -> None:
    if not overrides:
        return
    summary = "; ".join(item.reason for item in overrides)
    for item in selected:
        if item.source_type == "project" and item.portfolio_match_rank == 1:
            continue
        if item.override_reason is None:
            item.override_reason = summary
