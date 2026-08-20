"""Deterministic cover-letter positioning evidence pack (M4).

CareerProfile and PositioningPlan are candidate truth. JobAnalysis describes
employer needs. OpportunityAssessment is accepted only so tests can prove
``key_alignments`` are ignored. ApplicationStrategy supplies PortfolioMatch
ranks via ``portfolio_emphasis``; it does not authorise claims.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.document_positioning.builder import build_positioning_plan
from career_intelligence.document_positioning.letter_selection import (
    EvidenceSelection,
    SelectedEvidenceSource,
    select_cover_letter_evidence,
)
from career_intelligence.document_positioning.models import (
    PositioningPlan,
    SupportStatus,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.profile.models import CareerProfile

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_ML_LABELS = (
    "tensorflow",
    "pytorch",
    "keras",
    "scikit-learn",
    "machine learning",
    "deep learning",
)


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


class PackedForbidden(PackModel):
    requested_label: NonEmptyString
    may_not_claim: NonEmptyString
    reason: NonEmptyString
    identity: str | None = None


class PackedSource(PackModel):
    source_id: NonEmptyString
    source_type: NonEmptyString
    name: NonEmptyString
    organisation: str | None = None
    purpose: NonEmptyString
    employer_needs_covered: tuple[str, ...] = ()
    coverage_kinds: tuple[str, ...] = ()
    portfolio_match_rank: int | None = None
    override_reason: str | None = None
    facts: tuple[str, ...] = ()
    technologies: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    chapter: str | None = None


class PackedOverride(PackModel):
    project_id: NonEmptyString
    project_name: NonEmptyString
    portfolio_match_rank: int
    reason: NonEmptyString


class PackContact(PackModel):
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    github_url: str | None = None


class CoverLetterPositioningPack(PackModel):
    """Inspectable contract for the bounded cover-letter writer."""

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
    selected_sources: tuple[PackedSource, ...]
    portfolio_overrides: tuple[PackedOverride, ...]
    high_priority_needs: tuple[str, ...]
    opening_facts: tuple[str, ...]
    body_facts: tuple[str, ...]
    closing_facts: tuple[str, ...]
    allowed_employer_names: tuple[str, ...]
    allowed_project_names: tuple[str, ...]
    allowed_technologies: tuple[str, ...]
    commercial_ai_employment: bool
    candidate_has_ml_expertise: bool
    contact: PackContact
    constraints: tuple[str, ...]
    evidence_count_policy: NonEmptyString
    prose_role_title: NonEmptyString
    assessment_ignored: Literal[True] = True


def build_cover_letter_positioning_pack(
    job: JobAnalysis,
    profile: CareerProfile,
    *,
    positioning: PositioningPlan | None = None,
    strategy: ApplicationStrategy | None = None,
    assessment: OpportunityAssessment | None = None,
    contact: ContactDetails | None = None,
) -> CoverLetterPositioningPack:
    """Build the letter pack. ``assessment`` is intentionally unused."""
    _ = assessment
    plan = positioning or build_positioning_plan(job, profile, assessment=assessment)
    selection = select_cover_letter_evidence(profile, plan, strategy=strategy)
    return _pack_from_selection(
        job,
        profile,
        plan,
        selection,
        contact=contact,
    )


def _pack_from_selection(
    job: JobAnalysis,
    profile: CareerProfile,
    plan: PositioningPlan,
    selection: EvidenceSelection,
    *,
    contact: ContactDetails | None,
) -> CoverLetterPositioningPack:
    needs = tuple(_pack_need(item) for item in plan.employer_needs)
    claimable = tuple(
        dict.fromkeys(
            item.classification.promotable_profile_label or item.need.label
            for item in plan.employer_needs
            if item.classification.status is SupportStatus.SUPPORTED_DIRECT
            and item.classification.may_claim_requested
        )
    )
    related = tuple(
        dict.fromkeys(
            item.classification.promotable_profile_label
            for item in plan.employer_needs
            if item.classification.status is SupportStatus.SUPPORTED_RELATED
            and item.classification.promotable_profile_label
        )
    )
    unsupported = tuple(
        dict.fromkeys(
            item.need.label
            for item in plan.employer_needs
            if item.classification.status is SupportStatus.UNSUPPORTED
        )
    )
    sources = tuple(_pack_source(item) for item in selection.sources)
    overrides = tuple(
        PackedOverride(
            project_id=item.project_id,
            project_name=item.project_name,
            portfolio_match_rank=item.portfolio_match_rank,
            reason=item.reason,
        )
        for item in selection.overrides
    )
    forbidden = tuple(
        PackedForbidden(
            requested_label=item.requested_label,
            may_not_claim=item.may_not_claim,
            reason=item.reason,
            identity=item.identity,
        )
        for item in plan.forbidden_claims
    )
    allowed_orgs = _unique(
        [job.posting.company or "Employer"],
        [item.organisation for item in sources if item.organisation],
        [
            part
            for item in sources
            if item.source_type == "trajectory"
            for part in item.labels
        ],
    )
    allowed_projects = tuple(
        item.name for item in sources if item.source_type == "project"
    )
    allowed_tech = _unique(
        *[list(item.technologies) for item in sources],
        list(claimable),
        list(related),
    )
    commercial_ai = _has_commercial_ai_employment(profile)
    has_ml = _has_ml_expertise(profile, allowed_tech)
    pack_contact = _pack_contact(contact)
    posting = job.posting
    company = posting.company or "Employer"
    role_title = posting.title or profile.identity.target_role
    prose_role = _prose_role_title(
        role_title,
        job.role_family.family,
        forbidden=forbidden,
        unsupported=unsupported,
    )
    opening, body, closing = _facts_for_writer(
        company=company,
        role_title=prose_role,
        plan=plan,
        sources=sources,
        claimable=claimable,
        related=related,
        unsupported=unsupported,
    )
    return CoverLetterPositioningPack(
        company=company,
        role_title=role_title,
        role_family=job.role_family.family,
        trajectory_mode=plan.trajectory_mode,
        trajectory_rationale=plan.trajectory_rationale,
        include_methodology=plan.include_methodology,
        include_methodology_rationale=plan.include_methodology_rationale,
        employer_needs=needs,
        argument_spine=tuple(claim.statement for claim in plan.argument_spine),
        forbidden_claims=forbidden,
        claimable_direct_labels=claimable,
        related_profile_labels=related,
        unsupported_labels=unsupported,
        selected_sources=sources,
        portfolio_overrides=overrides,
        high_priority_needs=selection.high_priority_needs,
        opening_facts=opening,
        body_facts=body,
        closing_facts=closing,
        allowed_employer_names=tuple(allowed_orgs),
        allowed_project_names=allowed_projects,
        allowed_technologies=tuple(allowed_tech),
        commercial_ai_employment=commercial_ai,
        candidate_has_ml_expertise=has_ml,
        contact=pack_contact,
        constraints=_constraints(
            plan=plan,
            commercial_ai_employment=commercial_ai,
            candidate_has_ml_expertise=has_ml,
            related=related,
            unsupported=unsupported,
        ),
        evidence_count_policy=(
            "Default two evidence sources. A third is allowed only when it "
            "covers a distinct high-priority DIRECT or RELATED need not already "
            "represented. Maximum three. Sources may be projects, employment, "
            "independent engineering, certifications, or trajectory."
        ),
        prose_role_title=prose_role,
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


def _pack_source(item: SelectedEvidenceSource) -> PackedSource:
    return PackedSource(
        source_id=item.source_id,
        source_type=item.source_type,
        name=item.name,
        organisation=item.organisation,
        purpose=item.purpose,
        employer_needs_covered=item.employer_needs_covered,
        coverage_kinds=item.coverage_kinds,
        portfolio_match_rank=item.portfolio_match_rank,
        override_reason=item.override_reason,
        facts=item.facts,
        technologies=item.technologies,
        labels=item.labels,
        chapter=item.chapter,
    )


def _prose_role_title(
    title: str,
    role_family: str,
    *,
    forbidden: tuple[PackedForbidden, ...],
    unsupported: tuple[str, ...],
) -> str:
    """Avoid pasting vendor-stack job titles into writer prose."""
    folded = title.casefold()
    needles = [item.may_not_claim.casefold() for item in forbidden]
    needles.extend(label.casefold() for label in unsupported)
    if any(needle and len(needle) >= 4 and needle in folded for needle in needles):
        return role_family.replace("_", " ")
    return title


def _facts_for_writer(
    *,
    company: str,
    role_title: str,
    plan: PositioningPlan,
    sources: tuple[PackedSource, ...],
    claimable: tuple[str, ...],
    related: tuple[str, ...],
    unsupported: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    lead_source = sources[0].name if sources else "packed AI Engineering evidence"
    opening = (
        f"Target role is {role_title} at {company}.",
        f"Trajectory mode is {plan.trajectory_mode}. {plan.trajectory_rationale}",
        f"Lead evidence anchor: {lead_source}.",
        (
            "Authorised DIRECT capabilities: " + ", ".join(claimable[:4])
            if claimable
            else "No catalogue DIRECT capabilities; do not invent them."
        ),
        "Do not open with generic enthusiasm, excitement, or 'I am writing to apply'.",
    )
    body: list[str] = []
    for source in sources:
        covered = ", ".join(source.employer_needs_covered) or "supporting evidence"
        body.append(f"{source.name}: {source.purpose}")
        body.append(f"Need coverage: {covered}.")
        body.extend(source.facts[:3])
    if related:
        body.append(
            "RELATED profile evidence is "
            + ", ".join(related)
            + ". Promote that real capability. Never claim the employer's requested identity."
        )
    if plan.include_methodology:
        body.append(
            "Methodology may be mentioned only from packed CareerProfile "
            "engineering methodology; do not invent process claims."
        )
    closing = (
        f"Close by connecting packed evidence to {company}'s {role_title} work.",
        "Do not repeat the opening. Do not request a conversation with filler.",
        (
            "Unsupported identities must not be claimed: " + ", ".join(unsupported[:6])
            if unsupported
            else "No listed unsupported identities."
        ),
    )
    return opening, tuple(body), closing


def _pack_contact(contact: ContactDetails | None) -> PackContact:
    if contact is None:
        return PackContact()
    payload = contact.model_dump(exclude_none=True)
    return PackContact.model_validate(payload)


def _has_commercial_ai_employment(profile: CareerProfile) -> bool:
    for entry in profile.experience:
        if entry.kind != "employment":
            continue
        blob = f"{entry.title} {' '.join(entry.highlights)}".casefold()
        if "ai engineer" in blob or "artificial intelligence" in blob:
            return True
    return False


def _has_ml_expertise(profile: CareerProfile, allowed_tech: list[str]) -> bool:
    haystack = " ".join(allowed_tech).casefold()
    for skill in (*profile.skills.technical, *profile.skills.domain):
        haystack = f"{haystack} {skill.name.casefold()}"
    return any(label in haystack for label in _ML_LABELS)


def _constraints(
    *,
    plan: PositioningPlan,
    commercial_ai_employment: bool,
    candidate_has_ml_expertise: bool,
    related: tuple[str, ...],
    unsupported: tuple[str, ...],
) -> tuple[str, ...]:
    items = [
        "Use only facts in this evidence pack. Do not invent employment, "
        "technologies, metrics, qualifications, years, or project outcomes.",
        "Employer needs are job context, not candidate evidence.",
        "Express DIRECT capabilities as candidate capabilities.",
        "RELATED: promote the packed profile capability. Never claim the "
        "requested employer identity (AWS is not AWS Bedrock experience).",
        "Never claim UNSUPPORTED capabilities.",
        "Open with the target role/employer, the strongest truthful argument, "
        "and one or two packed evidence anchors. No generic enthusiasm.",
        "Organise body paragraphs around employer needs and selected sources, "
        "not a forced biography. Do not write duplicate source paragraphs.",
        "Keep the letter concise and recruiter-readable (about one page).",
        "Write in Australian English.",
        "Use prose_role_title when naming the vacancy. Do not paste vendor "
        "product lists from the posting title into candidate-claim sentences.",
        f"Trajectory mode is {plan.trajectory_mode}. It shapes emphasis; it is "
        "not a canned paragraph template.",
    ]
    if plan.trajectory_mode == "ai_lead":
        items.append(
            "Lead with current AI Engineering capability. Do not walk QA → "
            "data engineering → AI as the primary argument."
        )
    elif plan.trajectory_mode == "bridge":
        items.append(
            "Connect prior engineering/testing/data employment to this role as "
            "a transfer argument using only packed employment facts."
        )
    else:
        items.append(
            "The QA → data engineering → AI Engineering progression is part of "
            "the selling argument. Portfolio evidence supports the trajectory."
        )
    if not commercial_ai_employment:
        items.append(
            "There is no commercial AI Engineering employment. Describe applied "
            "AI work as independent / portfolio engineering."
        )
    if not candidate_has_ml_expertise:
        items.append(
            "Do not claim machine learning, deep learning, TensorFlow, PyTorch, "
            "or ML expertise."
        )
    if related:
        items.append("Related profile labels: " + ", ".join(related) + ".")
    if unsupported:
        items.append(
            "Unsupported labels (do not claim): " + ", ".join(unsupported[:8]) + "."
        )
    return tuple(items)


def _unique(*groups: list[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in groups:
        for item in group:
            if not item:
                continue
            text = item.strip()
            key = text.casefold()
            if not text or key in seen:
                continue
            seen.add(key)
            ordered.append(text)
    return ordered
