"""Unit tests for FR-008 M1 routing and spike helpers."""

from __future__ import annotations

from career_intelligence.orchestration import (
    SPIKE_NODE_SEQUENCE,
    describe_apply_side_effect_graph,
    describe_pre_approval_graph,
    describe_spike_graph,
    next_spike_node,
)
from career_intelligence.orchestration.routing import assert_node_is_next
from tests.unit.orchestration.helpers import make_control, make_state
from tests.unit.orchestration.m1_helpers import fixture_job_input, offline_runner


def test_spike_graph_sequence() -> None:
    assert describe_pre_approval_graph() == (
        "acquire",
        "validate_normalise",
        "analyse",
        "assess",
        "match",
        "strategy",
        "owner_review",
    )
    assert describe_apply_side_effect_graph() == ("persist", "record_decision")
    assert describe_spike_graph() == describe_pre_approval_graph() + describe_apply_side_effect_graph()
    assert SPIKE_NODE_SEQUENCE[0] == "acquire"


def test_next_node_advances_with_completed_records() -> None:
    state = make_state(control=make_control(status="running", current_node="acquire"))
    assert next_spike_node(state) == "acquire"

    # Simulate acquire completed via runner path in integration tests; here set records.
    from career_intelligence.orchestration.models import CompletedNodeRecord, ExecutionMetadata
    from tests.unit.orchestration.helpers import now

    state = make_state(
        control=make_control(status="running"),
        execution=ExecutionMetadata(
            completed_nodes=[
                CompletedNodeRecord(node_id="acquire", kind="deterministic", completed_at=now())
            ]
        ),
    )
    assert next_spike_node(state) == "validate_normalise"


def test_next_node_none_when_awaiting_or_terminal() -> None:
    from career_intelligence.orchestration import ApprovalState
    from tests.unit.orchestration.helpers import now

    awaiting = make_state(
        control=make_control(status="awaiting_owner", current_node="owner_review"),
        approval=ApprovalState(
            pending_kind="owner_review",
            pending_options=["apply", "skip", "defer"],
            pending_requested_at=now(),
        ),
    )
    assert next_spike_node(awaiting) is None

    done = make_state(control=make_control(status="completed", completed_at=now()))
    assert next_spike_node(done) is None


def test_assert_node_is_next_fail_closed() -> None:
    state = make_state()
    try:
        assert_node_is_next(state, "strategy")
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "strategy" in str(error)


def test_paste_job_input_defaults() -> None:
    job = fixture_job_input()
    assert "CIC-FIXTURE" in job.raw_text
    assert job.title is not None
