"""Internal extraction schema for FR-002 AI-backed extractors.

``JobAnalysisExtraction`` is the structured-output contract for extractors. It
intentionally excludes ``posting`` — the service alone binds the caller-supplied
``JobPosting``. Nested domain types are reused; they are not duplicated here.
"""

from __future__ import annotations

from pydantic import Field

from .models import (
    Compensation,
    EmploymentInfo,
    ExperienceRequirement,
    JobAnalysisModel,
    LocationInfo,
    Responsibility,
    RoleFamilyAssessment,
    SeniorityAssessment,
    TechnologyRequirement,
    WorkArrangement,
)


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
