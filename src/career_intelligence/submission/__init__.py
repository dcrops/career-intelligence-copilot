"""Public API for Submission Assistance (FR-012).

M0: typed attempts, evidence, transitions, append-only store.
M1: ``SubmissionOrchestrator``, adapter contract, fake / manual-assisted adapters.
"""

from __future__ import annotations

from .adapters import (
    ADAPTER_OUTCOME_STATUSES,
    AdapterOutcomeStatus,
    SubmissionAdapter,
    SubmissionAdapterRequest,
    SubmissionAdapterResult,
)
from .errors import (
    ErrorDetail,
    SubmissionAppendOnlyError,
    SubmissionAttemptNotFoundError,
    SubmissionChannelError,
    SubmissionDuplicateError,
    SubmissionError,
    SubmissionGateError,
    SubmissionStorageError,
    SubmissionTransitionError,
    SubmissionValidationError,
)
from .fake_adapter import FakeSubmissionAdapter
from .ids import new_submission_attempt_id
from .json_store import JsonDirectorySubmissionAttemptStore
from .manual_adapter import ManualAssistedAdapter
from .memory_store import InMemorySubmissionAttemptStore
from .models import (
    FAILURE_LIKE_STATUSES,
    SUBMISSION_STATUSES,
    SUCCESS_SUBMISSION_STATUSES,
    TERMINAL_SUBMISSION_STATUSES,
    PackageRef,
    SubmissionAttempt,
    SubmissionAttemptId,
    SubmissionChannel,
    SubmissionEvidence,
    SubmissionMode,
    SubmissionReadinessReport,
    SubmissionStatus,
)
from .orchestrator import DEFAULT_SUBMISSION_ATTEMPTS_ROOT, SubmissionOrchestrator
from .transitions import (
    apply_status_transition,
    validate_evidence_for_status,
    validate_status_transition,
)

__all__ = [
    "ADAPTER_OUTCOME_STATUSES",
    "DEFAULT_SUBMISSION_ATTEMPTS_ROOT",
    "FAILURE_LIKE_STATUSES",
    "SUBMISSION_STATUSES",
    "SUCCESS_SUBMISSION_STATUSES",
    "TERMINAL_SUBMISSION_STATUSES",
    "AdapterOutcomeStatus",
    "ErrorDetail",
    "FakeSubmissionAdapter",
    "InMemorySubmissionAttemptStore",
    "JsonDirectorySubmissionAttemptStore",
    "ManualAssistedAdapter",
    "PackageRef",
    "SubmissionAdapter",
    "SubmissionAdapterRequest",
    "SubmissionAdapterResult",
    "SubmissionAppendOnlyError",
    "SubmissionAttempt",
    "SubmissionAttemptId",
    "SubmissionAttemptNotFoundError",
    "SubmissionChannel",
    "SubmissionChannelError",
    "SubmissionDuplicateError",
    "SubmissionError",
    "SubmissionEvidence",
    "SubmissionGateError",
    "SubmissionMode",
    "SubmissionOrchestrator",
    "SubmissionReadinessReport",
    "SubmissionStatus",
    "SubmissionStorageError",
    "SubmissionTransitionError",
    "SubmissionValidationError",
    "apply_status_transition",
    "new_submission_attempt_id",
    "validate_evidence_for_status",
    "validate_status_transition",
]
