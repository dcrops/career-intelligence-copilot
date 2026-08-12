"""Public API for the opportunity-assessment capability (FR-003)."""

from .errors import (
    RETRYABLE_ASSESSMENT_VALIDATION_TYPES,
    UNRECOVERABLE_ASSESSMENT_VALIDATION_TYPES,
    ErrorDetail,
    OpportunityAssessmentError,
    OpportunityAssessmentValidationError,
    assessment_validation_is_retryable,
)
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
    "RETRYABLE_ASSESSMENT_VALIDATION_TYPES",
    "UNRECOVERABLE_ASSESSMENT_VALIDATION_TYPES",
    "assessment_validation_is_retryable",
]
