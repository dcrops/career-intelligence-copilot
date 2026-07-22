"""Public API for the opportunity-assessment capability (FR-003)."""

from .errors import ErrorDetail, OpportunityAssessmentError, OpportunityAssessmentValidationError
from .models import (
    AssessmentSummary,
    FitDimensionAssessment,
    FitFinding,
    FitJudgment,
    JobEvidenceRef,
    OpportunityAssessment,
    ProfileEvidenceRef,
)
from .service import OpportunityAssessmentService

__all__ = [
    "AssessmentSummary",
    "ErrorDetail",
    "FitDimensionAssessment",
    "FitFinding",
    "FitJudgment",
    "JobEvidenceRef",
    "OpportunityAssessment",
    "OpportunityAssessmentError",
    "OpportunityAssessmentService",
    "OpportunityAssessmentValidationError",
    "ProfileEvidenceRef",
]
