"""Typed domain models for FR-006 CV Generation (Phase A/B/C).

Phase A produces a trusted TailoringPlan — deterministic emphasis decisions.
Phase B produces a trusted TailoredCv — a pure rendering of an approved plan.
Phase C may optionally rewrite Professional Summary prose via an injected rewriter.

Neither artifact invents employment, skills, projects, dates, or certifications.
When rewrite is disabled, Phase B copies the profile summary.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import Identifier

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# Preserve trailing newlines in rendered Markdown (model-level strip would remove them).
RenderedMarkdown = Annotated[str, StringConstraints(min_length=1, strip_whitespace=False)]

ExperienceGuidanceKind = Literal["master_cv_only", "include_extended_history"]

JdPriorityKind = Literal["technology", "responsibility", "role_theme"]

CandidateSupportStatus = Literal["supported", "related", "unsupported"]

JobEvidenceSource = Literal[
    "role_family",
    "seniority",
    "technology",
    "responsibility",
    "experience_requirement",
    "compensation",
    "location",
    "work_arrangement",
    "employment",
]

ProfileEvidenceSource = Literal[
    "skill",
    "experience",
    "project",
    "certification",
    "goal",
    "preference",
    "identity",
]

PlanEvidenceOrigin = Literal["job_analysis", "career_profile", "application_strategy"]

_LIST_JOB_SOURCES = frozenset(
    {
        "technology",
        "responsibility",
        "experience_requirement",
    }
)

ExperienceKind = Literal[
    "employment",
    "independent_engineering",
    "professional_development",
]


class CvModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobEvidenceRef(CvModel):
    """Pointer to an analysed job requirement with optional supporting excerpt."""

    source: JobEvidenceSource
    item_index: int | None = Field(default=None, ge=0)
    name: NonEmptyString | None = None
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def list_sources_require_item_index(self) -> JobEvidenceRef:
        if self.source in _LIST_JOB_SOURCES and self.item_index is None:
            raise ValueError(f"{self.source} job evidence requires item_index")
        return self


class ProfileEvidenceRef(CvModel):
    """Pointer to a career-profile entity. ``ref`` must resolve at service validation."""

    source: ProfileEvidenceSource
    ref: NonEmptyString
    excerpt: NonEmptyString | None = None


class PlanEvidenceRef(CvModel):
    """Evidence citation for one TailoringPlan recommendation."""

    origin: PlanEvidenceOrigin
    job_evidence: JobEvidenceRef | None = None
    profile_evidence: ProfileEvidenceRef | None = None
    portfolio_project_id: Identifier | None = None
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def origin_fields_are_consistent(self) -> PlanEvidenceRef:
        if self.origin == "job_analysis":
            if self.job_evidence is None:
                raise ValueError("job_analysis evidence requires job_evidence")
            if self.profile_evidence is not None or self.portfolio_project_id is not None:
                raise ValueError(
                    "job_analysis evidence may only include job_evidence "
                    "(and optional excerpt)"
                )
        elif self.origin == "career_profile":
            if self.profile_evidence is None:
                raise ValueError("career_profile evidence requires profile_evidence")
            if self.job_evidence is not None or self.portfolio_project_id is not None:
                raise ValueError(
                    "career_profile evidence may only include profile_evidence "
                    "(and optional excerpt)"
                )
        elif self.origin == "application_strategy":
            if self.portfolio_project_id is None:
                raise ValueError(
                    "application_strategy evidence requires portfolio_project_id"
                )
            if self.job_evidence is not None or self.profile_evidence is not None:
                raise ValueError(
                    "application_strategy evidence may only include "
                    "portfolio_project_id (and optional excerpt)"
                )
        return self


class JdPriority(CvModel):
    """One ordered employer priority from the job analysis.

    ``candidate_support`` records whether the Career Profile can back CV emphasis
    for this priority (supported / related / unsupported). Unsupported priorities
    remain visible as hiring requirements but must not become summary themes or
    promoted skills.
    """

    rank: int = Field(ge=1)
    label: NonEmptyString
    kind: JdPriorityKind
    rationale: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)
    candidate_support: CandidateSupportStatus
    related_profile_capability: NonEmptyString | None = None


class EmphasisedProject(CvModel):
    """One portfolio project to emphasise, in TailoringPlan order."""

    rank: int = Field(ge=1)
    project_id: Identifier
    rationale: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class PromotedSkill(CvModel):
    """One profile skill to promote, in TailoringPlan order."""

    rank: int = Field(ge=1)
    skill_name: NonEmptyString
    category: Literal["technical", "domain", "soft"]
    rationale: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class DeprioritisedSkill(CvModel):
    """Profile skill retained but not emphasised for this opportunity."""

    skill_name: NonEmptyString
    category: Literal["technical", "domain", "soft"]
    rationale: NonEmptyString


class SummaryTheme(CvModel):
    """Theme the (future) rewritten summary should cover. Phase B does not rewrite."""

    rank: int = Field(ge=1)
    theme: NonEmptyString
    rationale: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class ExperienceGuidance(CvModel):
    """Which experience entries may appear on the tailored CV."""

    kind: ExperienceGuidanceKind
    rationale: NonEmptyString
    included_experience_ids: list[Identifier] = Field(default_factory=list)
    excluded_experience_ids: list[Identifier] = Field(default_factory=list)


class TailoringPlan(CvModel):
    """Trusted deterministic CV-emphasis plan for one opportunity.

    ``job_analysis`` is bound by TailoringPlanService from the caller-supplied
    ApplicationStrategy. The plan decides emphasis; it does not contain CV prose.
    """

    job_analysis: JobAnalysis
    application_tier: NonEmptyString
    pursuit_posture: NonEmptyString
    jd_priorities: list[JdPriority] = Field(default_factory=list)
    projects_to_emphasise: list[EmphasisedProject] = Field(default_factory=list)
    skills_to_promote: list[PromotedSkill] = Field(default_factory=list)
    skills_not_emphasised: list[DeprioritisedSkill] = Field(default_factory=list)
    summary_themes: list[SummaryTheme] = Field(default_factory=list)
    experience_guidance: ExperienceGuidance
    assumptions: list[NonEmptyString] = Field(default_factory=list)
    owner_review_recommended: Literal[True] = True
    insufficient_evidence: bool = False
    material_benefit_override: bool = False

    @model_validator(mode="after")
    def ranks_are_contiguous(self) -> TailoringPlan:
        for field_name in (
            "jd_priorities",
            "projects_to_emphasise",
            "skills_to_promote",
            "summary_themes",
        ):
            entries = getattr(self, field_name)
            ranks = [entry.rank for entry in entries]
            expected = list(range(1, len(entries) + 1))
            if ranks != expected:
                raise ValueError(
                    f"{field_name} ranks must be contiguous starting at 1; "
                    f"got {ranks}"
                )
        return self


class RenderedSkill(CvModel):
    skill_name: NonEmptyString
    category: Literal["technical", "domain", "soft"]
    emphasised: bool


class RenderedProject(CvModel):
    project_id: Identifier
    name: NonEmptyString
    summary: NonEmptyString
    technologies: list[NonEmptyString] = Field(default_factory=list)
    outcomes: list[NonEmptyString] = Field(default_factory=list)
    demonstrates: list[NonEmptyString] = Field(default_factory=list)


class RenderedExperience(CvModel):
    experience_id: Identifier
    kind: ExperienceKind
    organisation: NonEmptyString
    title: NonEmptyString
    start_date: NonEmptyString
    end_date: NonEmptyString | None = None
    location: NonEmptyString | None = None
    highlights: list[NonEmptyString] = Field(default_factory=list)
    technologies: list[NonEmptyString] = Field(default_factory=list)


class RenderedCertification(CvModel):
    certification_id: Identifier
    name: NonEmptyString
    issuer: NonEmptyString
    status: Literal["active", "expired"]


class TailoredCv(CvModel):
    """Trusted CV draft rendered from an approved TailoringPlan.

    Plan-owned sections (skills, projects, experience scope, summary themes)
    must match the TailoringPlan. Certifications are a fixed profile baseline
    (``certifications_source=profile_active_baseline``) — not tailored content.

    Phase B copies the profile summary when rewrite is disabled. Phase C may
    rewrite summary prose from the Tailoring Plan via an injected rewriter.
    Final external use always requires owner review.
    """

    job_analysis: JobAnalysis
    full_name: NonEmptyString
    target_role: NonEmptyString
    summary: NonEmptyString | None = None
    summary_source: Literal[
        "profile_copy",
        "openai_rewrite",
        "fixture_rewrite",
        "fallback_profile_copy",
    ] = "profile_copy"
    summary_themes: list[NonEmptyString] = Field(default_factory=list)
    skills: list[RenderedSkill] = Field(default_factory=list)
    projects: list[RenderedProject] = Field(default_factory=list)
    experience: list[RenderedExperience] = Field(default_factory=list)
    certifications: list[RenderedCertification] = Field(default_factory=list)
    certifications_source: Literal["profile_active_baseline"] = "profile_active_baseline"
    contact: dict[str, NonEmptyString] | None = None
    rendered_markdown: RenderedMarkdown
    owner_review_required: Literal[True] = True
    tailoring_plan_approved: Literal[True] = True
    experience_guidance_kind: ExperienceGuidanceKind
    assumptions: list[NonEmptyString] = Field(default_factory=list)
