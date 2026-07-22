"""Typed domain models for FR-002 Job Analysis.

These models describe the job posting only. They intentionally omit candidate-fit,
tier, portfolio-match, and apply/skip recommendation fields — those belong to FR-003+.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

CurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$"),
]

RoleFamily = Literal[
    "ai_engineering",
    "ai_solutions",
    "data_engineering",
    "software_engineering",
    "ml_engineering",
    "network_engineering",
    "ai_adjacent",
    "other",
    "unknown",
]

SeniorityLevel = Literal[
    "entry",
    "mid",
    "senior",
    "lead",
    "principal",
    "manager",
    "unknown",
]

RequirementLevel = Literal["required", "preferred", "unspecified"]

Clarity = Literal["stated", "unstated", "ambiguous"]

CompensationPeriod = Literal["year", "month", "day", "hour"]

WorkArrangementKind = Literal["onsite", "hybrid", "remote", "unspecified"]

WorkingHours = Literal["full_time", "part_time", "unspecified"]

EngagementType = Literal[
    "permanent",
    "fixed_term",
    "contract",
    "casual",
    "internship",
    "unspecified",
]


class JobAnalysisModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceEvidence(JobAnalysisModel):
    """Short grounded excerpt from the posting. Deliberately small — no offsets or IDs."""

    excerpt: NonEmptyString
    section: NonEmptyString | None = None


class JobPosting(JobAnalysisModel):
    """Raw job-description input supplied by the user."""

    raw_text: NonEmptyString
    title: NonEmptyString | None = None
    company: NonEmptyString | None = None
    source_url: AnyHttpUrl | None = None


class TechnologyRequirement(JobAnalysisModel):
    name: NonEmptyString
    level: RequirementLevel
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_required_for_claim(self) -> TechnologyRequirement:
        if not self.evidence:
            raise ValueError("technology requirement requires at least one evidence item")
        return self


class Responsibility(JobAnalysisModel):
    description: NonEmptyString
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_required_for_claim(self) -> Responsibility:
        if not self.evidence:
            raise ValueError("responsibility requires at least one evidence item")
        return self


class RoleFamilyAssessment(JobAnalysisModel):
    family: RoleFamily
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def known_family_requires_evidence(self) -> RoleFamilyAssessment:
        if self.family != "unknown" and not self.evidence:
            raise ValueError("known role family requires at least one evidence item")
        return self


class SeniorityAssessment(JobAnalysisModel):
    """Seniority as stated by the posting.

    - No seniority information: ``level="unknown"``, ``ambiguous=False``, empty
      ``candidate_levels`` and ``evidence``.
    - Conflicting / multiple plausible levels: ``ambiguous=True``, ``level="unknown"``,
      ``candidate_levels`` listing the supported non-unknown levels, plus evidence that
      cites the conflict. Do not force a single classification.
    """

    level: SeniorityLevel
    ambiguous: bool = False
    candidate_levels: list[SeniorityLevel] = Field(default_factory=list)
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def seniority_fields_are_consistent(self) -> SeniorityAssessment:
        if self.ambiguous:
            if self.level != "unknown":
                raise ValueError("ambiguous seniority must set level to 'unknown'")
            named = [level for level in self.candidate_levels if level != "unknown"]
            if not named:
                raise ValueError(
                    "ambiguous seniority requires at least one non-unknown candidate level"
                )
            if not self.evidence:
                raise ValueError("ambiguous seniority requires at least one evidence item")
        else:
            if self.candidate_levels:
                raise ValueError("candidate_levels are only allowed when ambiguous is true")
            if self.level != "unknown" and not self.evidence:
                raise ValueError("known seniority requires at least one evidence item")
        return self


class Compensation(JobAnalysisModel):
    """Compensation as written in the posting — no annualisation or currency conversion.

    Unstated compensation must have null amounts/currency/period/raw_text and empty
    evidence. Explicit nulls are equivalent to omission (structured-output friendly).
    Do not invent amounts or treat vague "competitive" wording as stated compensation.
    """

    clarity: Clarity
    minimum: float | None = Field(default=None, ge=0)
    maximum: float | None = Field(default=None, ge=0)
    currency: CurrencyCode | None = None
    period: CompensationPeriod | None = None
    raw_text: NonEmptyString | None = None
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def clarity_matches_content(self) -> Compensation:
        has_amount = self.minimum is not None or self.maximum is not None
        has_detail = has_amount or self.currency is not None or self.period is not None
        has_content = has_detail or self.raw_text is not None

        if self.clarity == "unstated":
            if has_content or self.evidence:
                raise ValueError(
                    "unstated compensation must omit amounts, currency, period, "
                    "raw_text, and evidence"
                )
        elif self.clarity in ("stated", "ambiguous"):
            if not has_content:
                raise ValueError(
                    f"{self.clarity} compensation requires minimum, maximum, or raw_text"
                )
            if not self.evidence:
                raise ValueError(
                    f"{self.clarity} compensation requires at least one evidence item"
                )

        if (
            self.minimum is not None
            and self.maximum is not None
            and self.maximum < self.minimum
        ):
            raise ValueError("maximum must be greater than or equal to minimum")
        return self


class LocationInfo(JobAnalysisModel):
    clarity: Clarity = "unstated"
    summary: NonEmptyString | None = None
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def clarity_matches_summary(self) -> LocationInfo:
        if self.clarity == "unstated":
            if self.summary is not None or self.evidence:
                raise ValueError("unstated location must omit summary and evidence")
        elif self.clarity in ("stated", "ambiguous"):
            if self.summary is None:
                raise ValueError(f"{self.clarity} location requires summary")
            if not self.evidence:
                raise ValueError(
                    f"{self.clarity} location requires at least one evidence item"
                )
        return self


class WorkArrangement(JobAnalysisModel):
    arrangement: WorkArrangementKind
    details: NonEmptyString | None = None
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def arrangement_matches_evidence(self) -> WorkArrangement:
        if self.arrangement == "unspecified":
            if self.evidence:
                raise ValueError("unspecified work arrangement must omit evidence")
            if self.details is not None:
                raise ValueError("unspecified work arrangement must omit details")
        elif not self.evidence:
            raise ValueError("known work arrangement requires at least one evidence item")
        return self


class EmploymentInfo(JobAnalysisModel):
    """Working hours and engagement type as separate dimensions.

    Populate a dimension only when the posting explicitly states it. Do not infer from
    hybrid/office wording, seniority, benefits, or recruiter tone. Known values require
    evidence; fully unspecified employment must omit evidence.
    """

    working_hours: WorkingHours = "unspecified"
    engagement_type: EngagementType = "unspecified"
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_when_either_dimension_known(self) -> EmploymentInfo:
        known = (
            self.working_hours != "unspecified" or self.engagement_type != "unspecified"
        )
        if known and not self.evidence:
            raise ValueError(
                "known employment information requires at least one evidence item"
            )
        if not known and self.evidence:
            raise ValueError("unspecified employment must omit evidence")
        return self


class ExperienceRequirement(JobAnalysisModel):
    """One evidence-backed experience requirement extracted from the posting."""

    description: NonEmptyString
    level: RequirementLevel
    minimum_years: float | None = Field(default=None, ge=0)
    maximum_years: float | None = Field(default=None, ge=0)
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_and_years_are_consistent(self) -> ExperienceRequirement:
        if not self.evidence:
            raise ValueError("experience requirement requires at least one evidence item")
        if (
            self.minimum_years is not None
            and self.maximum_years is not None
            and self.maximum_years < self.minimum_years
        ):
            raise ValueError("maximum_years must be greater than or equal to minimum_years")
        return self


class JobAnalysis(JobAnalysisModel):
    """Structured analysis of a job posting. Contains no candidate-fit fields."""

    posting: JobPosting
    role_family: RoleFamilyAssessment
    seniority: SeniorityAssessment
    technologies: list[TechnologyRequirement] = Field(default_factory=list)
    responsibilities: list[Responsibility] = Field(default_factory=list)
    compensation: Compensation
    location: LocationInfo = Field(default_factory=LocationInfo)
    work_arrangement: WorkArrangement
    employment: EmploymentInfo = Field(default_factory=EmploymentInfo)
    experience_requirements: list[ExperienceRequirement] = Field(default_factory=list)
