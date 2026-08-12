"""Unit tests for AAS-0 submit guard (nav vs final submission)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.submit_guard import (  # noqa: E402
    ControlClass,
    FinalSubmitGuardError,
    PageSignals,
    assert_may_activate,
    classify_control,
)


def test_apply_on_job_detail_is_navigation() -> None:
    page = PageSignals(
        url="https://www.seek.com.au/job/93837541",
        looks_like_job_detail=True,
    )
    assert classify_control("Apply", page=page) is ControlClass.NAVIGATION
    assert assert_may_activate("Apply", page=page) is ControlClass.NAVIGATION


def test_continue_and_next_are_navigation() -> None:
    page = PageSignals(looks_like_application_form=True)
    assert classify_control("Continue", page=page) is ControlClass.NAVIGATION
    assert classify_control("Next", page=page) is ControlClass.NAVIGATION
    assert classify_control("Save and continue", page=page) is ControlClass.NAVIGATION


def test_submit_application_is_final() -> None:
    page = PageSignals(looks_like_application_form=True)
    assert classify_control("Submit application", page=page) is ControlClass.FINAL_SUBMIT
    with pytest.raises(FinalSubmitGuardError, match="final-submission"):
        assert_may_activate("Submit application", page=page)


def test_bare_submit_is_final() -> None:
    page = PageSignals()
    assert classify_control("Submit", page=page) is ControlClass.FINAL_SUBMIT


def test_apply_on_review_page_is_final() -> None:
    page = PageSignals(
        looks_like_review_or_confirmation=True,
        looks_like_application_form=True,
        heading_text="Review your application",
    )
    assert classify_control("Apply", page=page) is ControlClass.FINAL_SUBMIT
    with pytest.raises(FinalSubmitGuardError):
        assert_may_activate("Apply", page=page)


def test_send_application_is_final() -> None:
    page = PageSignals(looks_like_review_or_confirmation=True)
    assert classify_control("Send application", page=page) is ControlClass.FINAL_SUBMIT


def test_bare_complete_on_form_is_ambiguous() -> None:
    page = PageSignals(looks_like_application_form=True)
    assert classify_control("Complete", page=page) is ControlClass.AMBIGUOUS
    with pytest.raises(FinalSubmitGuardError, match="cannot confidently classify"):
        assert_may_activate("Complete", page=page)


def test_review_heading_derives_final_for_apply() -> None:
    page = PageSignals(
        heading_text="Almost done — confirm your application",
        looks_like_application_form=True,
    )
    assert classify_control("Apply now", page=page) is ControlClass.FINAL_SUBMIT


def test_seek_job_url_apply_without_flags_is_navigation() -> None:
    page = PageSignals(url="https://www.seek.com.au/job/93837541")
    assert classify_control("Apply", page=page) is ControlClass.NAVIGATION


def test_seek_quick_apply_on_job_detail_is_navigation() -> None:
    page = PageSignals(
        url="https://www.seek.com.au/job/93837541",
        looks_like_job_detail=True,
    )
    assert classify_control("Quick apply", page=page) is ControlClass.NAVIGATION
    assert assert_may_activate("Quick apply", page=page) is ControlClass.NAVIGATION


def test_quick_apply_on_review_page_is_final() -> None:
    page = PageSignals(
        looks_like_review_or_confirmation=True,
        heading_text="Review your application",
    )
    assert classify_control("Quick apply", page=page) is ControlClass.FINAL_SUBMIT


def test_continue_with_word_joiner_is_navigation() -> None:
    page = PageSignals(looks_like_application_form=True)
    assert classify_control("Continue\u2060", page=page) is ControlClass.NAVIGATION


def test_review_and_submit_is_final() -> None:
    page = PageSignals(looks_like_application_form=True)
    assert classify_control("Review and submit", page=page) is ControlClass.FINAL_SUBMIT
