"""Immutable-ish helpers for updating WorkflowState during a run."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError

from .errors import ErrorDetail, WorkflowValidationError
from .events import WorkflowEvent, WorkflowEventType
from .models import (
    AcquisitionEnvelope,
    CompletedNodeRecord,
    RetryState,
    WorkflowErrorInfo,
    WorkflowState,
)
from .types import NodeKind


def utc_now() -> datetime:
    return datetime.now(UTC)


def _validate(state: WorkflowState) -> WorkflowState:
    try:
        return WorkflowState.model_validate(state.model_dump(mode="python"))
    except ValidationError as error:
        raise WorkflowValidationError(
            [ErrorDetail.from_pydantic(item) for item in error.errors()]
        ) from error


def replace_control(state: WorkflowState, **updates: object) -> WorkflowState:
    control = state.control.model_copy(update=updates)
    return _validate(state.model_copy(update={"control": control}))


def replace_acquisition(
    state: WorkflowState,
    acquisition: AcquisitionEnvelope,
) -> WorkflowState:
    return _validate(state.model_copy(update={"acquisition": acquisition}))


def replace_artefacts(state: WorkflowState, **updates: object) -> WorkflowState:
    artefacts = state.artefacts.model_copy(update=updates)
    return _validate(state.model_copy(update={"artefacts": artefacts}))


def replace_approval(state: WorkflowState, **updates: object) -> WorkflowState:
    approval = state.approval.model_copy(update=updates)
    return _validate(state.model_copy(update={"approval": approval}))


def append_event(state: WorkflowState, event: WorkflowEvent) -> WorkflowState:
    events = list(state.execution.events)
    events.append(event)
    execution = state.execution.model_copy(update={"events": events})
    return _validate(
        state.model_copy(
            update={
                "execution": execution,
                "control": state.control.model_copy(update={"updated_at": event.timestamp}),
            }
        )
    )


def mark_node_completed(
    state: WorkflowState,
    *,
    node_id: str,
    kind: NodeKind,
    completed_at: datetime | None = None,
) -> WorkflowState:
    stamp = completed_at or utc_now()
    completed = list(state.execution.completed_nodes)
    if any(item.node_id == node_id for item in completed):
        return state
    completed.append(
        CompletedNodeRecord(node_id=node_id, kind=kind, completed_at=stamp)
    )
    execution = state.execution.model_copy(update={"completed_nodes": completed})
    return _validate(state.model_copy(update={"execution": execution}))


def completed_node_ids(state: WorkflowState) -> set[str]:
    return {item.node_id for item in state.execution.completed_nodes}


def make_event(
    state: WorkflowState,
    event_type: WorkflowEventType,
    *,
    timestamp: datetime | None = None,
    **fields: object,
) -> WorkflowEvent:
    payload: dict[str, object] = {
        "event_type": event_type,
        "timestamp": timestamp or utc_now(),
        "run_id": state.run_id,
    }
    payload.update(fields)
    return WorkflowEvent.model_validate(payload)


def set_last_error(
    state: WorkflowState,
    *,
    message: str,
    recoverable: bool,
    node_id: str | None = None,
    detail: str | None = None,
) -> WorkflowState:
    info = WorkflowErrorInfo(
        message=message,
        recoverable=recoverable,
        node_id=node_id,
        detail=detail,
    )
    return replace_control(state, last_error=info, updated_at=utc_now())


def replace_retry(state: WorkflowState, retry: RetryState | None) -> WorkflowState:
    return _validate(state.model_copy(update={"retry": retry}))


def clear_retry(state: WorkflowState) -> WorkflowState:
    if state.retry is None:
        return state
    return replace_retry(state, None)
