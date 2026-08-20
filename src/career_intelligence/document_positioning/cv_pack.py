"""Deterministic CV positioning evidence pack (M3).

CareerProfile, Master CV locked prose, and PositioningPlan selected refs are
candidate truth. JobAnalysis describes employer needs. OpportunityAssessment
is accepted only so tests can prove ``key_alignments`` are ignored.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from career_intelligence.cv_generation.content_selection import (
    select_engineering_highlights,
)
from career_intelligence.cv_generation.master_adapt import (
    extract_master_highlights,
    extract_master_project_bodies,
    extract_master_summary,
)
from career_intelligence.cv_generation.models import TailoringPlan
from career_intelligence.document_positioning.models import (
    PositioningPlan,
    SupportStatus,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.profile.models import CareerProfile

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_MAX_HIGHLIGHTS = 4
_MAX_PROJECTS = 3
_MAX_EVIDENCE_SNIPPETS = 12
_MAX_SNIPPET_CHARS = 280


class PackModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


class PackedNeed(PackModel):
    """Employer requirement plus classification. Not candidate evidence."""

    label: NonEmptyString
    kind: NonEmptyString
    status: SupportStatus
    requested_identity: str | None = None
    promotable_profile_label: str | None = None
    may_claim_requested: bool
    employer_excerpt: str | None = None


class PackedEvidence(PackModel):
    """Authoritative candidate snippet. Never JD text."""

    ref: NonEmptyString
    source: Literal["skill", "experience", "project", "certification", "master_summary"]
    text: NonEmptyString


class PackedProject(PackModel):
    project_id: NonEmptyString
    name: NonEmptyString
    technologies: tuple[str, ...] = ()
    locked_body: NonEmptyString


class PackedForbidden(PackModel):
    requested_label: NonEmptyString
    may_not_claim: NonEmptyString
    reason: NonEmptyString
    identity: str | None = None


class CvPositioningPack(PackModel):
    """Inspectable contract for the bounded CV writer."""

    company: NonEmptyString
    role_title: NonEmptyString
    role_family: NonEmptyString
    trajectory_mode: NonEmptyString
    trajectory_rationale: NonEmptyString
    include_methodology: bool
    include_methodology_rationale: NonEmptyString
    employer_needs: tuple[PackedNeed, ...]
    argument_spine: tuple[str, ...]
    forbidden_claims: tuple[PackedForbidden, ...]
    claimable_direct_labels: tuple[str, ...]
    related_profile_labels: tuple[str, ...]
    unsupported_labels: tuple[str, ...]
    candidate_evidence: tuple[PackedEvidence, ...]
    master_summary: NonEmptyString
    master_highlights: tuple[str, ...]
    selected_highlights: tuple[str, ...]
    selected_projects: tuple[PackedProject, ...]
    assessment_ignored: Literal[True] = True


def build_cv_positioning_pack(
    job: JobAnalysis,
    profile: CareerProfile,
    positioning: PositioningPlan,
    tailoring: TailoringPlan,
    master_markdown: str,
    *,
    assessment: OpportunityAssessment | None = None,
) -> CvPositioningPack:
    """Build the CV pack. ``assessment`` is intentionally unused."""
    _ = assessment
    master_summary = extract_master_summary(master_markdown) or (
        profile.identity.summary
    )
    master_highlights = tuple(extract_master_highlights(master_markdown))
    if not master_highlights:
        master_highlights = tuple(profile.selected_engineering_highlights)
    project_bodies = extract_master_project_bodies(master_markdown)

    needs = tuple(_pack_need(item) for item in positioning.employer_needs)
    claimable = tuple(
        dict.fromkeys(
            item.classification.promotable_profile_label
            or item.need.label
            for item in positioning.employer_needs
            if item.classification.status is SupportStatus.SUPPORTED_DIRECT
            and item.classification.may_claim_requested
        )
    )
    related = tuple(
        dict.fromkeys(
            item.classification.promotable_profile_label
            for item in positioning.employer_needs
            if item.classification.status is SupportStatus.SUPPORTED_RELATED
            and item.classification.promotable_profile_label
        )
    )
    unsupported = tuple(
        dict.fromkeys(
            item.need.label
            for item in positioning.employer_needs
            if item.classification.status is SupportStatus.UNSUPPORTED
        )
    )
    terms = [
        *claimable,
        *related,
        *(theme.theme for theme in tailoring.summary_themes),
    ]
    selected_highlights = tuple(
        select_engineering_highlights(
            list(master_highlights),
            terms,
            max_items=_MAX_HIGHLIGHTS,
        )
    )
    projects = _pack_projects(profile, tailoring, project_bodies)
    evidence = _pack_evidence(profile, positioning, master_summary)
    forbidden = tuple(
        PackedForbidden(
            requested_label=item.requested_label,
            may_not_claim=item.may_not_claim,
            reason=item.reason,
            identity=item.identity,
        )
        for item in positioning.forbidden_claims
    )
    posting = job.posting
    return CvPositioningPack(
        company=posting.company or "Employer",
        role_title=posting.title or profile.identity.target_role,
        role_family=job.role_family.family,
        trajectory_mode=positioning.trajectory_mode,
        trajectory_rationale=positioning.trajectory_rationale,
        include_methodology=positioning.include_methodology,
        include_methodology_rationale=positioning.include_methodology_rationale,
        employer_needs=needs,
        argument_spine=tuple(claim.statement for claim in positioning.argument_spine),
        forbidden_claims=forbidden,
        claimable_direct_labels=claimable,
        related_profile_labels=related,
        unsupported_labels=unsupported,
        candidate_evidence=evidence,
        master_summary=master_summary,
        master_highlights=master_highlights,
        selected_highlights=selected_highlights,
        selected_projects=projects,
    )


def _pack_need(item) -> PackedNeed:
    classification = item.classification
    return PackedNeed(
        label=item.need.label,
        kind=item.need.kind,
        status=classification.status,
        requested_identity=classification.requested_identity,
        promotable_profile_label=classification.promotable_profile_label,
        may_claim_requested=classification.may_claim_requested,
        employer_excerpt=item.need.excerpt,
    )


def _pack_projects(
    profile: CareerProfile,
    tailoring: TailoringPlan,
    project_bodies: dict[str, str],
) -> tuple[PackedProject, ...]:
    by_id = {project.id: project for project in profile.projects}
    packed: list[PackedProject] = []
    for item in tailoring.projects_to_emphasise:
        if len(packed) >= _MAX_PROJECTS:
            break
        project = by_id.get(item.project_id)
        if project is None:
            continue
        body = project_bodies.get(project.name)
        if not body:
            continue
        packed.append(
            PackedProject(
                project_id=project.id,
                name=project.name,
                technologies=tuple(project.technologies),
                locked_body=body,
            )
        )
    return tuple(packed)


def _pack_evidence(
    profile: CareerProfile,
    positioning: PositioningPlan,
    master_summary: str,
) -> tuple[PackedEvidence, ...]:
    items: list[PackedEvidence] = []
    seen: set[str] = set()

    def _add(ref: str, source: str, text: str) -> None:
        key = ref.casefold()
        if key in seen or not text.strip():
            return
        seen.add(key)
        items.append(
            PackedEvidence(
                ref=ref,
                source=source,  # type: ignore[arg-type]
                text=_clip(text.strip()),
            )
        )
        if len(items) >= _MAX_EVIDENCE_SNIPPETS:
            return

    _add("master_summary", "master_summary", master_summary)
    for ref in positioning.selected_evidence_refs:
        if len(items) >= _MAX_EVIDENCE_SNIPPETS:
            break
        text = _resolve_ref_text(profile, ref.ref)
        if text:
            _add(ref.ref, ref.source, text)
    return tuple(items)


def _resolve_ref_text(profile: CareerProfile, ref: str) -> str | None:
    kind, _, identifier = ref.partition(":")
    if kind == "skill":
        return identifier
    if kind == "experience":
        for entry in profile.experience:
            if entry.id == identifier:
                highlights = " ".join(entry.highlights[:2])
                return f"{entry.title} at {entry.organisation}. {highlights}".strip()
    if kind == "project":
        for project in profile.projects:
            if project.id == identifier:
                return f"{project.name}: {project.summary}"
    if kind == "certification":
        for cert in profile.certifications:
            if cert.id == identifier:
                return cert.name
    return None


def _clip(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= _MAX_SNIPPET_CHARS:
        return cleaned
    return cleaned[: _MAX_SNIPPET_CHARS - 1].rstrip() + "…"
