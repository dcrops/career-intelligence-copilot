"""Public API for Application Preparation Orchestration (FR-011).

Thin coordinator over existing Opportunity and Application Package services.
Does not extend the FR-008 workflow runner and does not own package business rules.
"""

from .errors import (
    ApplicationPreparationError,
    ApplicationPreparationStorageError,
    ApplicationPreparationValidationError,
    ErrorDetail,
    PreparationRunNotFoundError,
)
from .memory_store import InMemoryPreparationRunStore
from .models import (
    PREPARATION_STEPS,
    CompletedStepRecord,
    PackageResultRef,
    PreparationErrorInfo,
    PreparationRunId,
    PreparationRunState,
    PreparationStatus,
    PreparationStepId,
)
from .service import DEFAULT_PREPARATION_RUNS_ROOT, ApplicationPreparationOrchestrator

__all__ = [
    "DEFAULT_PREPARATION_RUNS_ROOT",
    "PREPARATION_STEPS",
    "ApplicationPreparationError",
    "ApplicationPreparationOrchestrator",
    "ApplicationPreparationStorageError",
    "ApplicationPreparationValidationError",
    "CompletedStepRecord",
    "ErrorDetail",
    "InMemoryPreparationRunStore",
    "PackageResultRef",
    "PreparationErrorInfo",
    "PreparationRunId",
    "PreparationRunNotFoundError",
    "PreparationRunState",
    "PreparationStatus",
    "PreparationStepId",
]
