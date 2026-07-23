"""Public API for durable Opportunity persistence (M1)."""

from .errors import (
    ErrorDetail,
    OpportunityArtifactExistsError,
    OpportunityError,
    OpportunityNotFoundError,
    OpportunityStorageError,
    OpportunityValidationError,
)
from .models import (
    ARTIFACT_FILENAMES,
    Opportunity,
    OpportunityIdentity,
    OutcomeRecord,
    OwnerDecisionRecord,
    PipelineStatus,
    SourceKind,
    StrategySummary,
)
from .service import OpportunityService

__all__ = [
    "ARTIFACT_FILENAMES",
    "ErrorDetail",
    "Opportunity",
    "OpportunityArtifactExistsError",
    "OpportunityError",
    "OpportunityIdentity",
    "OpportunityNotFoundError",
    "OpportunityService",
    "OpportunityStorageError",
    "OpportunityValidationError",
    "OutcomeRecord",
    "OwnerDecisionRecord",
    "PipelineStatus",
    "SourceKind",
    "StrategySummary",
]
