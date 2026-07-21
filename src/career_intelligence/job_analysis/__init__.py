"""Public API for the job-analysis capability (FR-002)."""

from .errors import ErrorDetail, JobAnalysisError, JobAnalysisValidationError
from .models import (
    Compensation,
    EmploymentInfo,
    EngagementType,
    ExperienceRequirement,
    JobAnalysis,
    JobPosting,
    LocationInfo,
    RequirementLevel,
    Responsibility,
    RoleFamily,
    RoleFamilyAssessment,
    SeniorityAssessment,
    SeniorityLevel,
    SourceEvidence,
    TechnologyRequirement,
    WorkArrangement,
    WorkingHours,
)
from .service import JobAnalysisService

__all__ = [
    "Compensation",
    "EmploymentInfo",
    "EngagementType",
    "ErrorDetail",
    "ExperienceRequirement",
    "JobAnalysis",
    "JobAnalysisError",
    "JobAnalysisService",
    "JobAnalysisValidationError",
    "JobPosting",
    "LocationInfo",
    "RequirementLevel",
    "Responsibility",
    "RoleFamily",
    "RoleFamilyAssessment",
    "SeniorityAssessment",
    "SeniorityLevel",
    "SourceEvidence",
    "TechnologyRequirement",
    "WorkArrangement",
    "WorkingHours",
]
