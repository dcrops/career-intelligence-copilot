"""Unit tests for workflow execution events (FR-008 M0)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.orchestration import WORKFLOW_EVENT_TYPES, WorkflowEvent
from tests.unit.orchestration.helpers import fixed_run_id, make_event, now


def test_all_declared_event_types_constructible() -> None:
    for event_type in WORKFLOW_EVENT_TYPES:
        event = make_event(event_type)
        assert event.event_type == event_type
        assert event.run_id == fixed_run_id()


def test_node_started_requires_node_id() -> None:
    with pytest.raises(ValidationError, match="node_id"):
        WorkflowEvent.model_validate(
            {
                "event_type": "node_started",
                "timestamp": now(),
                "run_id": fixed_run_id(),
            }
        )


def test_node_failed_requires_recoverable_and_duration() -> None:
    with pytest.raises(ValidationError, match="recoverable"):
        WorkflowEvent.model_validate(
            {
                "event_type": "node_failed",
                "timestamp": now(),
                "run_id": fixed_run_id(),
                "node_id": "assess",
                "duration_ms": 10,
            }
        )

    with pytest.raises(ValidationError, match="duration_ms"):
        WorkflowEvent.model_validate(
            {
                "event_type": "node_failed",
                "timestamp": now(),
                "run_id": fixed_run_id(),
                "node_id": "assess",
                "recoverable": True,
            }
        )


def test_checkpoint_written_requires_reason() -> None:
    with pytest.raises(ValidationError, match="checkpoint_reason"):
        WorkflowEvent.model_validate(
            {
                "event_type": "checkpoint_written",
                "timestamp": now(),
                "run_id": fixed_run_id(),
            }
        )


def test_approval_events_require_fields() -> None:
    with pytest.raises(ValidationError, match="approval_kind"):
        make_event("approval_requested", approval_kind=None)

    with pytest.raises(ValidationError, match="decision"):
        make_event("approval_received", decision=None)


def test_run_level_events_forbid_node_id() -> None:
    with pytest.raises(ValidationError, match="must not include node_id"):
        make_event("run_started", node_id="analyse")


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        WorkflowEvent.model_validate(
            {
                "event_type": "run_completed",
                "timestamp": now(),
                "run_id": fixed_run_id(),
                "token_count": 99,
            }
        )
