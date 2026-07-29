"""Deterministic routing for the FR-008 application workflow graph."""

from __future__ import annotations

from .models import WorkflowState
from .state_helpers import completed_node_ids
from .types import TERMINAL_WORKFLOW_STATUSES

# Pre-approval linear graph. ``acquire`` uses any AcquisitionAdapter.
PRE_APPROVAL_SEQUENCE: tuple[str, ...] = (
    "acquire",
    "validate_normalise",
    "analyse",
    "assess",
    "match",
    "strategy",
    "owner_review",
)

# Post-approval apply side effects (M2). Skip/defer complete without these nodes.
APPLY_SIDE_EFFECT_SEQUENCE: tuple[str, ...] = (
    "persist",
    "record_decision",
)

# Back-compat alias used by tests/docs.
SPIKE_NODE_SEQUENCE: tuple[str, ...] = PRE_APPROVAL_SEQUENCE + APPLY_SIDE_EFFECT_SEQUENCE


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

    # Owner review complete; post-approval routing depends on recorded decision.
    decision = state.approval.owner_decision
    if decision is None:
        return None
    if decision in {"skip", "defer"}:
        return None
    if decision == "apply":
        for node_id in APPLY_SIDE_EFFECT_SEQUENCE:
            if node_id not in completed:
                return node_id
        return None

    return None


def assert_node_is_next(state: WorkflowState, node_id: str) -> None:
    """Fail closed when a node executes out of order."""
    expected = next_spike_node(state)
    if expected != node_id:
        raise ValueError(
            f"Invalid node order: refused to run '{node_id}' "
            f"(expected '{expected}')"
        )


def apply_side_effects_complete(state: WorkflowState) -> bool:
    """True when apply path has finished persist + record_decision (or N/A)."""
    decision = state.approval.owner_decision
    if decision in {"skip", "defer"}:
        return True
    if decision != "apply":
        return False
    completed = completed_node_ids(state)
    return all(node_id in completed for node_id in APPLY_SIDE_EFFECT_SEQUENCE)
