"""Typed domain models for FR-007 Cover Letter Generation.

Phase A produces a trusted CoverLetterPlan — structured composition decisions.
Phase B produces a trusted CoverLetter — deterministic prose from an approved plan.

Neither artifact invents employers, technologies, metrics, or achievements.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import Identifier

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RenderedMarkdown = Annotated[str, StringConstraints(min_length=1, strip_whitespace=False)]

PlanEvidenceOrigin = Literal[
    "job_analysis",
    "career_profile",
    "application_strategy",
    "portfolio_match",
]

JobEvidenceSource = Literal[
    "role_family",
    "responsibility",
    "technology",
    "seniority",
]

ProfileEvidenceSource = Literal[
    "identity",
    "skill",
    "experience",
    "project",
]

EvidenceKind = Literal[
    "commercial_experience",
    "portfolio_project",
    "engineering_practice",
    "capability",
]

ClosingApproach = Literal["conversation_request", "contribution_focus"]


class CoverLetterModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PlanEvidenceRef(CoverLetterModel):
    """Pointer into a validated upstream artifact — never free-form invention."""

    origin: PlanEvidenceOrigin
    job_source: JobEvidenceSource | None = None
    job_index: int | None = Field(default=None, ge=0)
    profile_source: ProfileEvidenceSource | None = None
    profile_id: Identifier | None = None
    portfolio_project_id: Identifier | None = None
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def origin_fields_are_consistent(self) -> PlanEvidenceRef:
        if self.origin == "job_analysis":
            if self.job_source is None:
                raise ValueError("job_analysis evidence requires job_source")
            if self.profile_source is not None or self.profile_id is not None:
                raise ValueError("job_analysis evidence may not include profile fields")
            if self.portfolio_project_id is not None:
                raise ValueError("job_analysis evidence may not include portfolio_project_id")
        elif self.origin == "career_profile":
            if self.profile_source is None:
                raise ValueError("career_profile evidence requires profile_source")
            if self.job_source is not None or self.job_index is not None:
                raise ValueError("career_profile evidence may not include job fields")
            if self.portfolio_project_id is not None:
                raise ValueError(
                    "career_profile evidence may not include portfolio_project_id"
                )
        elif self.origin == "application_strategy":
            if (
                self.job_source is not None
                or self.profile_source is not None
                or self.portfolio_project_id is not None
            ):
                raise ValueError(
                    "application_strategy evidence may only include optional excerpt"
                )
        elif self.origin == "portfolio_match":
            if self.portfolio_project_id is None:
                raise ValueError("portfolio_match evidence requires portfolio_project_id")
            if self.job_source is not None or self.profile_source is not None:
                raise ValueError(
                    "portfolio_match evidence may not include job or profile fields"
                )
        return self


class CompanyAlignment(CoverLetterModel):
    """Why this company — grounded in JobAnalysis / strategy signals."""

    company: NonEmptyString
    alignment_hook: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class RoleMotivation(CoverLetterModel):
    """Why this role — grounded in responsibilities and role family."""

    role_title: NonEmptyString
    motivation: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class RelevantEvidence(CoverLetterModel):
    """One profile-backed claim suitable for the letter body."""

    kind: EvidenceKind
    claim: NonEmptyString
    project_id: Identifier | None = None
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class StrongestProject(CoverLetterModel):
    """Portfolio project selected for the letter (profile + JD evidence fit)."""

    rank: int = Field(ge=1)
    project_id: Identifier
    project_name: NonEmptyString
    emphasis: NonEmptyString
    selection_reason: NonEmptyString
    business_outcome: NonEmptyString
    fit_focus: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class ClosingStrategy(CoverLetterModel):
    """How the letter should close — plan intent, not invented company claims."""

    approach: ClosingApproach
    intent: NonEmptyString
    evidence: list[PlanEvidenceRef] = Field(min_length=1)


class CoverLetterPlan(CoverLetterModel):
    """Trusted intermediate plan for cover letter composition (FR-007 Phase A).

    Authoritative for company alignment, role motivation, evidence selection,
    project emphasis, and closing strategy. Does not contain final letter prose.
    """

    job_analysis: JobAnalysis
    application_tier: NonEmptyString
    pursuit_posture: NonEmptyString
    company_alignment: CompanyAlignment
    role_motivation: RoleMotivation
    relevant_evidence: list[RelevantEvidence] = Field(min_length=1, max_length=4)
    strongest_projects: list[StrongestProject] = Field(default_factory=list, max_length=3)
    closing_strategy: ClosingStrategy
    assumptions: list[NonEmptyString] = Field(default_factory=list)
    owner_review_recommended: Literal[True] = True
    insufficient_evidence: bool = False
    material_benefit_override: bool = False


class CoverLetter(CoverLetterModel):
    """Trusted rendered cover letter (FR-007 Phase B)."""

    full_name: NonEmptyString
    company: NonEmptyString
    role_title: NonEmptyString
    salutation: NonEmptyString
    paragraphs: list[NonEmptyString] = Field(min_length=3, max_length=5)
    rendered_markdown: RenderedMarkdown
    contact: dict[str, NonEmptyString] | None = None
    job_analysis: JobAnalysis
    application_tier: NonEmptyString
    pursuit_posture: NonEmptyString
    assumptions: list[NonEmptyString] = Field(default_factory=list)
    cover_letter_plan_approved: Literal[True] = True
    owner_review_required: Literal[True] = True
    composition_source: Literal["deterministic_composition"] = "deterministic_composition"
