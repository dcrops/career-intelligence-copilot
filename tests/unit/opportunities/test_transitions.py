"""Unit tests for PipelineStatus transition rules (M2)."""

from __future__ import annotations

import pytest

from career_intelligence.opportunities import OpportunityTransitionError
from career_intelligence.opportunities.transitions import validate_status_transition


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("assessed", "preparing"),
        ("assessed", "submitted"),
        ("assessed", "deferred"),
        ("preparing", "submitted"),
        ("submitted", "interviewing"),
        ("interviewing", "offer"),
        ("offer", "accepted"),
        ("submitted", "rejected"),
        ("interviewing", "withdrawn"),
        ("assessed", "assessed"),  # same-status allowed
    ],
)
def test_valid_transitions(current: str, new: str) -> None:
    validate_status_transition(current, new)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("assessed", "interviewing"),
        ("assessed", "offer"),
        ("preparing", "interviewing"),
        ("accepted", "interviewing"),
        ("rejected", "submitted"),
        ("withdrawn", "assessed"),
        ("offer", "interviewing"),
    ],
)
def test_invalid_transitions(current: str, new: str) -> None:
    with pytest.raises(OpportunityTransitionError):
        validate_status_transition(current, new)  # type: ignore[arg-type]
