"""Typed execution events for FR-008 workflow runs (minimal audit trail)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .types import NodeKind, OwnerDecisionKind

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

WorkflowEventType = Literal[
    "run_started",
    "node_started",
    "node_succeeded",
    "node_failed",
    "retry_scheduled",
    "retry_exhausted",
    "checkpoint_written",
    "approval_requested",
    "approval_received",
    "run_resumed",
    "run_completed",
    "run_cancelled",
]

CheckpointReason = Literal["approval", "milestone", "failure", "terminal"]

WORKFLOW_EVENT_TYPES: tuple[WorkflowEventType, ...] = get_args(WorkflowEventType)


class EventModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkflowEvent(EventModel):
    """One append-only execution history entry.

    Field presence is constrained by ``event_type`` so the log stays typed
    without a large discriminated-union tree.
    """

    event_type: WorkflowEventType
    timestamp: datetime
    run_id: NonEmptyString
    node_id: NonEmptyString | None = None
    node_kind: NodeKind | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    message: NonEmptyString | None = None
    recoverable: bool | None = None
    checkpoint_reason: CheckpointReason | None = None
    approval_kind: NonEmptyString | None = None
    decision: OwnerDecisionKind | None = None
    attempt: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def fields_match_event_type(self) -> WorkflowEvent:
        et = self.event_type

        if et in {"node_started", "node_succeeded", "node_failed"} and self.node_id is None:
            raise ValueError(f"{et} requires node_id")

        if et == "node_failed" and self.recoverable is None:
            raise ValueError("node_failed requires recoverable")

        if et in {"node_succeeded", "node_failed"} and self.duration_ms is None:
            raise ValueError(f"{et} requires duration_ms")

        if et in {"retry_scheduled", "retry_exhausted"}:
            if self.node_id is None:
                raise ValueError(f"{et} requires node_id")
            if self.attempt is None:
                raise ValueError(f"{et} requires attempt")

        if et == "retry_scheduled" and self.recoverable is not True:
            raise ValueError("retry_scheduled requires recoverable=True")

        if et == "checkpoint_written" and self.checkpoint_reason is None:
            raise ValueError("checkpoint_written requires checkpoint_reason")

        if et == "approval_requested" and self.approval_kind is None:
            raise ValueError("approval_requested requires approval_kind")

        if et == "approval_received" and self.decision is None:
            raise ValueError("approval_received requires decision")

        if et in {"run_started", "run_completed", "run_cancelled", "run_resumed"}:
            if self.node_id is not None:
                raise ValueError(f"{et} must not include node_id")

        return self
