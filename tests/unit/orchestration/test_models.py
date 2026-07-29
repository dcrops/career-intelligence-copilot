"""Unit tests for workflow state models (FR-008 M0)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_intelligence.orchestration import (
    ApprovalState,
    DomainArtefacts,
    ExecutionMetadata,
    WorkflowErrorInfo,
    WorkflowState,
    new_workflow_run_id,
)
from tests.unit.orchestration.helpers import (
    fixed_run_id,
    make_acquisition,
    make_control,
    make_event,
    make_state,
    now,
)


def test_new_workflow_run_id_shape() -> None:
    run_id = new_workflow_run_id()
    assert run_id.startswith("wfr_")
    assert len(run_id) == 4 + 26


def test_minimal_running_state_validates() -> None:
    state = make_state()
    assert state.run_id == fixed_run_id()
    assert state.status == "running"
    assert state.acquisition is not None
    assert state.acquisition.source_kind == "paste"
    assert state.artefacts.job_analysis is None


def test_round_trip_serialisation() -> None:
    state = make_state(
        control=make_control(current_node="strategy"),
        execution=ExecutionMetadata(
            events=[make_event("run_started"), make_event("node_started")],
            completed_nodes=[],
        ),
    )
    restored = WorkflowState.model_validate(state.model_dump(mode="json"))
    assert restored == state


def test_rejects_invalid_run_id() -> None:
    with pytest.raises(ValidationError):
        make_control(run_id="not-a-run-id")


def test_awaiting_owner_requires_pending_approval() -> None:
    with pytest.raises(ValidationError, match="awaiting_owner"):
        make_state(control=make_control(status="awaiting_owner"))


def test_awaiting_owner_with_pending_approval_ok() -> None:
    state = make_state(
        control=make_control(status="awaiting_owner", current_node="owner_review"),
        approval=ApprovalState(
            pending_kind="owner_review",
            pending_options=["apply", "skip", "defer"],
            pending_message="Review application strategy before persisting.",
            pending_requested_at=now(),
        ),
    )
    assert state.approval.pending_kind == "owner_review"
    assert "apply" in state.approval.pending_options


def test_running_must_not_have_pending_approval() -> None:
    with pytest.raises(ValidationError, match="running"):
        make_state(
            approval={
                "pending_kind": "owner_review",
                "pending_options": ["apply"],
                "pending_requested_at": now(),
            }
        )


def test_completed_requires_completed_at_and_clears_pending() -> None:
    with pytest.raises(ValidationError, match="completed_at"):
        make_state(control=make_control(status="completed"))

    state = make_state(
        control=make_control(
            status="completed",
            current_node=None,
            completed_at=now(),
            updated_at=now(),
        )
    )
    assert state.control.completed_at is not None


def test_terminal_must_not_leave_pending_approval() -> None:
    with pytest.raises(ValidationError, match="pending approval"):
        make_state(
            control=make_control(status="completed", completed_at=now()),
            approval={
                "pending_kind": "owner_review",
                "pending_options": ["apply"],
                "pending_requested_at": now(),
            },
        )


def test_completed_must_clear_last_error() -> None:
    with pytest.raises(ValidationError, match="last_error"):
        make_state(
            control=make_control(
                status="completed",
                completed_at=now(),
                last_error=WorkflowErrorInfo(message="boom", recoverable=False),
            )
        )


def test_failed_may_retain_last_error() -> None:
    state = make_state(
        control=make_control(
            status="failed",
            completed_at=now(),
            last_error=WorkflowErrorInfo(
                message="OpenAI timeout",
                recoverable=True,
                node_id="assess",
            ),
        )
    )
    assert state.control.last_error is not None
    assert state.control.last_error.node_id == "assess"


def test_approval_pending_options_require_kind() -> None:
    with pytest.raises(ValidationError):
        ApprovalState.model_validate({"pending_options": ["apply"]})


def test_owner_decision_requires_decided_at() -> None:
    with pytest.raises(ValidationError, match="decided_at"):
        ApprovalState.model_validate({"owner_decision": "apply"})


def test_events_must_match_run_id() -> None:
    with pytest.raises(ValidationError, match="run_id"):
        make_state(
            execution=ExecutionMetadata(
                events=[make_event("run_started", run_id=new_workflow_run_id())]
            )
        )


def test_acquisition_rejects_empty_raw_content() -> None:
    with pytest.raises(ValidationError):
        make_acquisition(raw_content="   ")


def test_acquisition_provenance_fields_round_trip() -> None:
    envelope = make_acquisition(
        source_kind="url",
        source_url="https://www.seek.com.au/job/123",
        source_identifier="123",
        warnings=["title inferred from first line"],
    )
    assert envelope.source_kind == "url"
    assert str(envelope.source_url).startswith("https://")
    assert envelope.warnings == ["title inferred from first line"]


def test_domain_artefacts_default_empty() -> None:
    artefacts = DomainArtefacts()
    assert artefacts.profile is None
    assert artefacts.opportunity_id is None


def test_opportunity_id_ref_shape() -> None:
    artefacts = DomainArtefacts(opportunity_id="opp_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert artefacts.opportunity_id.startswith("opp_")

    with pytest.raises(ValidationError):
        DomainArtefacts(opportunity_id="opp_bad")


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        WorkflowState.model_validate(
            {
                "control": make_control().model_dump(mode="json"),
                "unexpected": True,
            }
        )


def test_cancelled_terminal() -> None:
    state = make_state(
        control=make_control(
            status="cancelled",
            completed_at=datetime(2026, 7, 29, 13, 0, 0, tzinfo=UTC),
            current_node=None,
        )
    )
    assert state.status == "cancelled"
