"""Internal extraction schema for FR-002 AI-backed extractors.

``JobAnalysisExtraction`` is the structured-output contract for extractors. It
intentionally excludes ``posting`` — the service alone binds the caller-supplied
``JobPosting``. Nested domain types are reused; they are not duplicated here.

``posting_identity`` is extraction-only metadata used by the service to fill
missing ``JobPosting.title`` / ``company`` when the caller did not supply them.
It is never part of the trusted ``JobAnalysis`` schema.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from .models import (
    Compensation,
    EmploymentInfo,
    ExperienceRequirement,
    JobAnalysisModel,
    LocationInfo,
    NonEmptyString,
    Responsibility,
    RoleFamilyAssessment,
    SeniorityAssessment,
    SourceEvidence,
    TechnologyRequirement,
    WorkArrangement,
)


class ExtractedPostingIdentity(JobAnalysisModel):
    """Optional title/company extracted from the posting when not caller-supplied.

    Values may be null when identity cannot be established from the text. A non-null
    title or company requires at least one supporting evidence excerpt.
    """

    title: NonEmptyString | None = None
    company: NonEmptyString | None = None
    title_evidence: list[SourceEvidence] = Field(default_factory=list)
    company_evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def claimed_identity_requires_evidence(self) -> ExtractedPostingIdentity:
        if self.title is not None and not self.title_evidence:
            raise ValueError("extracted title requires at least one evidence item")
        if self.company is not None and not self.company_evidence:
            raise ValueError("extracted company requires at least one evidence item")
        return self


class JobAnalysisExtraction(JobAnalysisModel):
    """Fields an extractor may produce. Excludes ``posting`` by design."""

    role_family: RoleFamilyAssessment
    seniority: SeniorityAssessment
    technologies: list[TechnologyRequirement] = Field(default_factory=list)
    responsibilities: list[Responsibility] = Field(default_factory=list)
    compensation: Compensation
    location: LocationInfo = Field(default_factory=LocationInfo)
    work_arrangement: WorkArrangement
    employment: EmploymentInfo = Field(default_factory=EmploymentInfo)
    experience_requirements: list[ExperienceRequirement] = Field(default_factory=list)
    posting_identity: ExtractedPostingIdentity = Field(
        default_factory=ExtractedPostingIdentity
    )
