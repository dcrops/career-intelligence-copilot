"""Explicit translation between orchestration and opportunity decision kinds."""

from __future__ import annotations

from career_intelligence.opportunities import (
    OwnerDecisionKind as OpportunityOwnerDecisionKind,
)

from .types import OwnerDecisionKind as WorkflowOwnerDecisionKind

_MAP: dict[WorkflowOwnerDecisionKind, OpportunityOwnerDecisionKind] = {
    "apply": "apply",
    "skip": "skip",
    "defer": "defer",
}


def to_opportunity_decision(
    decision: WorkflowOwnerDecisionKind,
) -> OpportunityOwnerDecisionKind:
    """Map workflow owner decision → OpportunityService decision at the boundary.

    Literals are intentionally duplicated across packages (bounded contexts).
    This function is the only sanctioned translation point for FR-008 M2.
    """
    try:
        return _MAP[decision]
    except KeyError as error:
        raise ValueError(f"Unsupported workflow owner decision: {decision!r}") from error
