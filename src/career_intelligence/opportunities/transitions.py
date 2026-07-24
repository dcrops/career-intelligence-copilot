"""Simple PipelineStatus transition rules for M2 (not a workflow engine)."""

from __future__ import annotations

from .errors import OpportunityTransitionError
from .models import PIPELINE_STATUSES, TERMINAL_STATUSES, PipelineStatus

# Allowed forward moves. Same-status is always allowed (outcome-only updates).
_ALLOWED: dict[PipelineStatus, frozenset[PipelineStatus]] = {
    "assessed": frozenset({"deferred", "preparing", "submitted", "withdrawn"}),
    "deferred": frozenset({"assessed", "preparing", "submitted", "withdrawn"}),
    "preparing": frozenset({"submitted", "deferred", "withdrawn"}),
    "submitted": frozenset({"interviewing", "offer", "rejected", "withdrawn"}),
    "interviewing": frozenset({"interviewing", "offer", "rejected", "withdrawn"}),
    "offer": frozenset({"accepted", "rejected", "withdrawn"}),
    "accepted": frozenset(),
    "rejected": frozenset(),
    "withdrawn": frozenset(),
}


def validate_status_transition(
    current: PipelineStatus,
    new: PipelineStatus,
) -> None:
    """Raise ``OpportunityTransitionError`` when ``current -> new`` is invalid."""
    if current == new:
        return
    if current not in PIPELINE_STATUSES or new not in PIPELINE_STATUSES:
        raise OpportunityTransitionError(
            f"Unknown pipeline status transition: {current!r} -> {new!r}"
        )
    if current in TERMINAL_STATUSES:
        raise OpportunityTransitionError(
            f"Cannot change status from terminal state '{current}' to '{new}'"
        )
    allowed = _ALLOWED[current]
    if new not in allowed:
        raise OpportunityTransitionError(
            f"Invalid status transition: '{current}' -> '{new}'. "
            f"Allowed: {', '.join(sorted(allowed)) or '(none — terminal)'}"
        )
