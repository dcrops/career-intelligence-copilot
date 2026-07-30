"""Deterministic routing for the FR-008 application workflow graph."""

from __future__ import annotations

from .models import WorkflowState
from .state_helpers import completed_node_ids
from .types import TERMINAL_WORKFLOW_STATUSES

# Pre-approval linear graph. ``acquire`` uses any AcquisitionAdapter.
# ``persist`` runs before ``owner_review`` (FR-009 M1 / ADR-004): a successfully
# strategised job is durable before the owner decides anything.
PRE_APPROVAL_SEQUENCE: tuple[str, ...] = (
    "acquire",
    "validate_normalise",
    "analyse",
    "assess",
    "match",
    "strategy",
    "persist",
    "owner_review",
)

# Post-decision side effects. Runs for apply, skip, and defer — all three update
# the same durable Opportunity created before owner review.
POST_DECISION_SEQUENCE: tuple[str, ...] = ("record_decision",)

# Nodes with durable side effects. Their failures pause the run as resumable
# rather than discarding completed analysis work.
SIDE_EFFECT_NODE_IDS: frozenset[str] = frozenset({"persist", "record_decision"})

# Back-compat alias used by tests/docs.
SPIKE_NODE_SEQUENCE: tuple[str, ...] = PRE_APPROVAL_SEQUENCE + POST_DECISION_SEQUENCE


def next_spike_node(state: WorkflowState) -> str | None:
    """Return the next node id to execute, or None when paused/terminal/done.

    Routing is pure and inspectable — no LLM involvement.
    """
    if state.status in TERMINAL_WORKFLOW_STATUSES:
        return None
    if state.status == "awaiting_owner":
        return None

    completed = completed_node_ids(state)

    for node_id in PRE_APPROVAL_SEQUENCE:
        if node_id not in completed:
            return node_id

    # Owner review complete; post-decision routing needs a recorded decision.
    decision = state.approval.owner_decision
    if decision is None:
        return None

    for node_id in POST_DECISION_SEQUENCE:
        if node_id not in completed:
            return node_id
    return None


def assert_node_is_next(state: WorkflowState, node_id: str) -> None:
    """Fail closed when a node executes out of order."""
    expected = next_spike_node(state)
    if expected != node_id:
        raise ValueError(
            f"Invalid node order: refused to run '{node_id}' "
            f"(expected '{expected}')"
        )


def post_decision_complete(state: WorkflowState) -> bool:
    """True when the recorded decision has been written to the Opportunity."""
    if state.approval.owner_decision is None:
        return False
    completed = completed_node_ids(state)
    return all(node_id in completed for node_id in POST_DECISION_SEQUENCE)
