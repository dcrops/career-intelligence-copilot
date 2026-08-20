"""Final-review stage detection must ignore stepper-only 'Review and submit'."""

from __future__ import annotations

import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.session_handoff import (  # noqa: E402
    build_final_review_handoff,
    looks_like_final_submit_label,
)
from aas0.state_progress import (  # noqa: E402
    is_final_review_page,
    looks_like_stepper_review_label,
)
from aas0.submit_guard import (  # noqa: E402
    ControlClass,
    PageSignals,
    classify_control,
)

_STEPPER = (
    "Choose documents\nAnswer employer questions\n"
    "Update SEEK Profile\nReview and submit\n"
)

_QUESTIONS = (
    _STEPPER
    + "Answer employer questions\n"
    "Please elaborate your exposure to AI?\n"
    "Continue\n"
)

_PROFILE = (
    _STEPPER
    + "Update SEEK Profile\n"
    "Career history\nEducation\nContinue\n"
)

_REVIEW = (
    _STEPPER
    + "Review and submit\n"
    "Documents included\n"
    "You answered 7 out of 7\n"
    "Submit application\n"
)


def test_employer_questions_with_stepper_is_not_final_review() -> None:
    assert is_final_review_page(_QUESTIONS) is False
    assert looks_like_stepper_review_label("Review and submit") is True
    assert looks_like_final_submit_label("Review and submit") is False


def test_update_seek_profile_with_stepper_is_not_final_review() -> None:
    assert is_final_review_page(_PROFILE) is False


def test_actual_review_page_is_final_review() -> None:
    assert is_final_review_page(_REVIEW) is True
    assert looks_like_final_submit_label("Submit application") is True


def test_handoff_still_never_clicks_submit() -> None:
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.submit_clicked_by_automation is False
    assert handoff.automation_stopped is True
    review = PageSignals(looks_like_review_or_confirmation=True)
    assert classify_control("Submit application", page=review) is ControlClass.FINAL_SUBMIT
