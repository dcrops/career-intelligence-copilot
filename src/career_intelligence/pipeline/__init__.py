"""Public API for Application Pipeline Tracking (FR-013).

M1: contracts + append-only event store.
M2: PipelineTrackingService dual-write (ADR-005).
M3: owner CLI.
M4: derived reporting + CSV export (no domain redesign).
"""

from __future__ import annotations

from .constants import ACTIVE_PIPELINE_STATUSES
from .errors import (
    ErrorDetail,
    PipelineAppendOnlyError,
    PipelineConsistencyError,
    PipelineDivergenceError,
    PipelineError,
    PipelineEventNotFoundError,
    PipelinePartialWriteError,
    PipelineStorageError,
    PipelineTransitionError,
    PipelineValidationError,
)
from .ids import new_pipeline_event_id
from .json_store import JsonDirectoryPipelineEventStore
from .memory_store import InMemoryPipelineEventStore
from .models import (
    PIPELINE_EVENT_KINDS,
    PackageEvidenceRef,
    PipelineEvent,
    PipelineEventId,
    PipelineEventKind,
    PipelineEvidence,
)
from .projection import (
    FoldedLifecycleState,
    LifecycleProjection,
    fold_lifecycle_state,
    projection_from_event,
)
from .reporting import (
    DEFAULT_PIPELINE_EXPORT_PATH,
    PIPELINE_EXPORT_COLUMNS,
    AgeingItem,
    FollowUpItem,
    PipelineSummaryReport,
    build_summary_report,
    days_in_current_status,
    export_pipeline_csv,
)
from .service import (
    DEFAULT_PIPELINE_EVENTS_ROOT,
    PipelineApplyResult,
    PipelineDivergenceReport,
    PipelineTrackingService,
)
from .store import PipelineEventStore
from .transitions import (
    validate_event_contract,
    validate_pipeline_status_change,
)

__all__ = [
    "ACTIVE_PIPELINE_STATUSES",
    "DEFAULT_PIPELINE_EVENTS_ROOT",
    "DEFAULT_PIPELINE_EXPORT_PATH",
    "PIPELINE_EVENT_KINDS",
    "PIPELINE_EXPORT_COLUMNS",
    "AgeingItem",
    "ErrorDetail",
    "FoldedLifecycleState",
    "FollowUpItem",
    "InMemoryPipelineEventStore",
    "JsonDirectoryPipelineEventStore",
    "LifecycleProjection",
    "PackageEvidenceRef",
    "PipelineAppendOnlyError",
    "PipelineApplyResult",
    "PipelineConsistencyError",
    "PipelineDivergenceError",
    "PipelineDivergenceReport",
    "PipelineError",
    "PipelineEvent",
    "PipelineEventId",
    "PipelineEventKind",
    "PipelineEventNotFoundError",
    "PipelineEventStore",
    "PipelineEvidence",
    "PipelinePartialWriteError",
    "PipelineStorageError",
    "PipelineSummaryReport",
    "PipelineTrackingService",
    "PipelineTransitionError",
    "PipelineValidationError",
    "build_summary_report",
    "days_in_current_status",
    "export_pipeline_csv",
    "fold_lifecycle_state",
    "new_pipeline_event_id",
    "projection_from_event",
    "validate_event_contract",
    "validate_pipeline_status_change",
]
