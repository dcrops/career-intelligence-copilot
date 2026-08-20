"""Deterministic PositioningPlan builder.

Inputs: JobAnalysis (employer needs) + CareerProfile (candidate evidence).
OpportunityAssessment is accepted only so callers can pass it; summary
``key_alignments`` and other assessment free text are never read as candidate
truth. No LLM.
"""

from __future__ import annotations

from career_intelligence.document_positioning.catalogue import (
    aliases_for_identity,
    classify_requirement,
    first_alias_in_text,
    identities_mentioned_in_text,
    normalise_label,
    resolve_identity,
)
from career_intelligence.document_positioning.evidence import (
    collect_evidence_refs,
    profile_capability_labels,
)
from career_intelligence.document_positioning.models import (
    CV_REWRITE_SURFACE,
    LOCKED_MASTER_SECTIONS,
    ArgumentClaim,
    CandidateEvidenceRef,
    ClassifiedNeed,
    EmployerNeed,
    ForbiddenClaim,
    PositioningPlan,
    SupportStatus,
)
from career_intelligence.document_positioning.policies import (
    decide_include_methodology,
    decide_trajectory,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.profile.models import CareerProfile

_SHORT_UNKNOWN_TOKEN_LIMIT = 4
_MAX_PORTFOLIO_CLAIMS = 3


def build_positioning_plan(
    job: JobAnalysis,
    profile: CareerProfile,
    *,
    assessment: OpportunityAssessment | None = None,
) -> PositioningPlan:
    """Build a deterministic PositioningPlan from verified CIC artefacts.

    ``assessment`` is intentionally unused. It exists so tests can prove that
    ``key_alignments`` cannot establish candidate capability.
    """
    _ = assessment
    labels = profile_capability_labels(profile)
    needs = _extract_employer_needs(job)
    classified: list[ClassifiedNeed] = []
    for need in needs:
        result = classify_requirement(need.label, labels)
        refs: tuple[CandidateEvidenceRef, ...] = ()
        if result.status is not SupportStatus.UNSUPPORTED:
            refs = collect_evidence_refs(
                profile,
                identity=result.promotable_identity,
                label=result.promotable_profile_label or need.label,
            )
            if result.status is SupportStatus.SUPPORTED_RELATED:
                refs = tuple(
                    ref
                    for ref in refs
                    if not _ref_claims_requested(
                        ref,
                        requested_label=need.label,
                        requested_identity=result.requested_identity,
                    )
                )
        classified.append(
            ClassifiedNeed(need=need, classification=result, evidence_refs=refs)
        )

    selected = _unique_refs(
        ref for item in classified for ref in item.evidence_refs
    )
    include_methodology, methodology_rationale = decide_include_methodology(
        job, profile
    )
    trajectory_mode, trajectory_rationale = decide_trajectory(job, profile)
    spine = _build_argument_spine(
        classified,
        profile,
        trajectory_mode=trajectory_mode,
        trajectory_rationale=trajectory_rationale,
    )
    forbidden = _build_forbidden_claims(classified)
    return PositioningPlan(
        employer_needs=tuple(classified),
        argument_spine=spine,
        forbidden_claims=forbidden,
        selected_evidence_refs=selected,
        include_methodology=include_methodology,
        include_methodology_rationale=methodology_rationale,
        trajectory_mode=trajectory_mode,
        trajectory_rationale=trajectory_rationale,
        cv_rewrite_surface=CV_REWRITE_SURFACE,
        locked_master_sections=LOCKED_MASTER_SECTIONS,
    )


def _extract_employer_needs(job: JobAnalysis) -> list[EmployerNeed]:
    needs: list[EmployerNeed] = []
    seen_identities: set[str] = set()
    seen_norms: set[str] = set()

    def _try_add(
        *,
        kind: str,
        label: str,
        level: str | None,
        item_index: int,
        excerpt: str | None,
    ) -> None:
        identity = resolve_identity(label)
        norm = normalise_label(label)
        if not norm:
            return
        if identity is not None and identity in seen_identities:
            return
        if identity is None and norm in seen_norms:
            return
        if identity is not None:
            seen_identities.add(identity)
        seen_norms.add(norm)
        needs.append(
            EmployerNeed(
                rank=len(needs) + 1,
                kind=kind,  # type: ignore[arg-type]
                label=label,
                level=level,  # type: ignore[arg-type]
                item_index=item_index,
                excerpt=excerpt,
            )
        )

    for index, tech in enumerate(job.technologies):
        excerpt = tech.evidence[0].excerpt if tech.evidence else None
        _try_add(
            kind="technology",
            label=tech.name,
            level=tech.level,
            item_index=index,
            excerpt=excerpt,
        )

    for index, requirement in enumerate(job.experience_requirements):
        excerpt = (
            requirement.evidence[0].excerpt if requirement.evidence else None
        )
        mentioned = identities_mentioned_in_text(requirement.description)
        if mentioned:
            for identity in mentioned:
                alias = first_alias_in_text(requirement.description, identity)
                _try_add(
                    kind="experience_requirement",
                    label=alias or identity,
                    level=requirement.level,
                    item_index=index,
                    excerpt=excerpt,
                )
        elif len(normalise_label(requirement.description).split()) <= (
            _SHORT_UNKNOWN_TOKEN_LIMIT
        ):
            _try_add(
                kind="experience_requirement",
                label=requirement.description,
                level=requirement.level,
                item_index=index,
                excerpt=excerpt,
            )

    for index, responsibility in enumerate(job.responsibilities):
        excerpt = (
            responsibility.evidence[0].excerpt
            if responsibility.evidence
            else None
        )
        for identity in identities_mentioned_in_text(responsibility.description):
            alias = first_alias_in_text(responsibility.description, identity)
            _try_add(
                kind="responsibility",
                label=alias or identity,
                level=None,
                item_index=index,
                excerpt=excerpt,
            )

    return needs


def _build_argument_spine(
    classified: list[ClassifiedNeed],
    profile: CareerProfile,
    *,
    trajectory_mode: str,
    trajectory_rationale: str,
) -> tuple[ArgumentClaim, ...]:
    claims: list[ArgumentClaim] = []
    for item in classified:
        result = item.classification
        if result.status is SupportStatus.SUPPORTED_DIRECT:
            claims.append(
                ArgumentClaim(
                    kind="direct",
                    statement=(
                        f"Claim '{result.requested_label}' as a candidate "
                        f"capability via profile evidence "
                        f"'{result.promotable_profile_label}'."
                    ),
                    evidence_refs=item.evidence_refs,
                    need_rank=item.need.rank,
                )
            )
        elif result.status is SupportStatus.SUPPORTED_RELATED:
            claims.append(
                ArgumentClaim(
                    kind="related",
                    statement=(
                        f"Do not claim '{result.requested_label}'. Promote "
                        f"'{result.promotable_profile_label}' as related "
                        "candidate evidence for this employer need."
                    ),
                    evidence_refs=item.evidence_refs,
                    need_rank=item.need.rank,
                )
            )
        elif result.status is SupportStatus.UNSUPPORTED:
            claims.append(
                ArgumentClaim(
                    kind="gap",
                    statement=(
                        f"Gap: '{result.requested_label}' is unsupported by "
                        "CareerProfile evidence and must not be claimed."
                    ),
                    evidence_refs=(),
                    need_rank=item.need.rank,
                )
            )

    claims.append(
        ArgumentClaim(
            kind="trajectory",
            statement=(
                f"Trajectory mode is {trajectory_mode}. {trajectory_rationale}"
            ),
        )
    )

    project_ids = [
        ref.ref.removeprefix("project:")
        for item in classified
        if item.classification.status is not SupportStatus.UNSUPPORTED
        for ref in item.evidence_refs
        if ref.source == "project"
    ]
    seen_projects: set[str] = set()
    ordered_projects: list[str] = []
    for project_id in project_ids:
        if project_id in seen_projects:
            continue
        seen_projects.add(project_id)
        ordered_projects.append(project_id)
    by_id = {project.id: project for project in profile.projects}
    for project_id in ordered_projects[:_MAX_PORTFOLIO_CLAIMS]:
        project = by_id.get(project_id)
        if project is None:
            continue
        claims.append(
            ArgumentClaim(
                kind="portfolio",
                statement=(
                    f"Use portfolio project '{project.name}' as packed "
                    "evidence; keep Master project body unchanged."
                ),
                evidence_refs=(
                    CandidateEvidenceRef(
                        source="project", ref=f"project:{project.id}"
                    ),
                ),
            )
        )
    packed_ids = {
        claim.evidence_refs[0].ref.removeprefix("project:")
        for claim in claims
        if claim.kind == "portfolio" and claim.evidence_refs
    }
    for project in profile.projects:
        if len(packed_ids) >= _MAX_PORTFOLIO_CLAIMS:
            break
        if project.id in packed_ids:
            continue
        packed_ids.add(project.id)
        claims.append(
            ArgumentClaim(
                kind="portfolio",
                statement=(
                    f"Use portfolio project '{project.name}' as packed "
                    "evidence; keep Master project body unchanged. Do not "
                    "treat this project as evidence for unsupported employer "
                    "technologies."
                ),
                evidence_refs=(
                    CandidateEvidenceRef(
                        source="project", ref=f"project:{project.id}"
                    ),
                ),
            )
        )
    return tuple(claims)


def _build_forbidden_claims(
    classified: list[ClassifiedNeed],
) -> tuple[ForbiddenClaim, ...]:
    claims: list[ForbiddenClaim] = []
    seen: set[tuple[str, str]] = set()

    def _add(
        requested_label: str,
        may_not_claim: str,
        reason: str,
        identity: str | None,
    ) -> None:
        key = (normalise_label(may_not_claim), reason)
        if key in seen:
            return
        seen.add(key)
        claims.append(
            ForbiddenClaim(
                requested_label=requested_label,
                may_not_claim=may_not_claim,
                reason=reason,  # type: ignore[arg-type]
                identity=identity,
            )
        )

    for item in classified:
        result = item.classification
        if result.status is SupportStatus.SUPPORTED_RELATED:
            _add(
                result.requested_label,
                result.requested_label,
                "related_unclaimable",
                result.requested_identity,
            )
            if result.requested_identity is not None:
                for alias in aliases_for_identity(result.requested_identity):
                    _add(
                        result.requested_label,
                        alias,
                        "related_unclaimable",
                        result.requested_identity,
                    )
        elif result.status is SupportStatus.UNSUPPORTED:
            _add(
                result.requested_label,
                result.requested_label,
                "unsupported",
                result.requested_identity,
            )
            if result.requested_identity is not None:
                for alias in aliases_for_identity(result.requested_identity):
                    _add(
                        result.requested_label,
                        alias,
                        "unsupported",
                        result.requested_identity,
                    )
    return tuple(claims)


def _unique_refs(refs: object) -> tuple[CandidateEvidenceRef, ...]:
    unique: list[CandidateEvidenceRef] = []
    seen: set[str] = set()
    for ref in refs:  # type: ignore[assignment]
        if ref.ref in seen:
            continue
        seen.add(ref.ref)
        unique.append(ref)
    return tuple(unique)


def _ref_claims_requested(
    ref: CandidateEvidenceRef,
    *,
    requested_label: str,
    requested_identity: str | None,
) -> bool:
    """Drop refs whose identifier is the unclaimable requested capability."""
    needle = requested_identity or normalise_label(requested_label)
    if not needle:
        return False
    haystack = normalise_label(ref.ref.replace(":", " ").replace("_", " "))
    requested_tokens = set(needle.replace("_", " ").split())
    return bool(requested_tokens) and requested_tokens <= set(haystack.split())
