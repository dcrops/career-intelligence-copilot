"""Unit tests for node contracts (FR-008 M0)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.orchestration import (
    NodeFailure,
    NodeOutcome,
    NodeSpec,
    NodeSuccess,
    WorkflowNode,
)
from tests.unit.orchestration.helpers import make_state


def test_known_node_spec_validates() -> None:
    spec = NodeSpec(
        node_id="analyse",
        display_name="Job Analysis",
        kind="llm_backed",
        description="FR-002 JobAnalysisService boundary",
    )
    assert spec.kind == "llm_backed"


def test_extension_node_id_allowed() -> None:
    spec = NodeSpec(node_id="x_spike_probe", display_name="Spike probe", kind="deterministic")
    assert spec.node_id.startswith("x_")


def test_unknown_node_id_rejected() -> None:
    with pytest.raises(ValidationError, match="Unknown node_id"):
        NodeSpec(node_id="scrape_everything", display_name="Bad", kind="agentic")


def test_agentic_kind_reserved_but_valid() -> None:
    spec = NodeSpec(
        node_id="x_future_agent",
        display_name="Future agent",
        kind="agentic",
    )
    assert spec.kind == "agentic"


def test_node_outcome_requires_exactly_one_branch() -> None:
    state = make_state()
    with pytest.raises(ValidationError, match="exactly one"):
        NodeOutcome()

    with pytest.raises(ValidationError, match="exactly one"):
        NodeOutcome(
            success=NodeSuccess(state=state),
            failure=NodeFailure(message="nope"),
        )


def test_node_outcome_success_and_failure() -> None:
    state = make_state()
    ok = NodeOutcome(success=NodeSuccess(state=state))
    assert ok.success is not None
    assert ok.failure is None

    err = NodeOutcome(
        failure=NodeFailure(message="timeout", recoverable=True, detail="HTTP 429")
    )
    assert err.failure is not None
    assert err.failure.recoverable is True


def test_protocol_accepts_structural_implementation() -> None:
    class StubNode:
        @property
        def spec(self) -> NodeSpec:
            return NodeSpec(
                node_id="match",
                display_name="Portfolio Match",
                kind="deterministic",
            )

        def execute(self, state):  # type: ignore[no-untyped-def]
            return NodeOutcome(success=NodeSuccess(state=state))

    node: WorkflowNode = StubNode()
    assert isinstance(node, WorkflowNode)
    outcome = node.execute(make_state())
    assert outcome.success is not None
