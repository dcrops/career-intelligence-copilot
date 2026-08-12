"""Regression tests for AAS-0 Choose Documents loop / state-progress guards."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.state_progress import (  # noqa: E402
    CoverLetterGateError,
    PageFingerprint,
    SameStateRetryGuard,
    assert_cover_letter_radio_checked,
    assert_may_continue_documents_step,
    detect_validation_messages,
    fingerprint_from_text,
    state_advanced,
)


def test_cover_letter_radio_must_be_checked_before_upload() -> None:
    with pytest.raises(CoverLetterGateError, match="not checked"):
        assert_cover_letter_radio_checked(False)
    assert_cover_letter_radio_checked(True)


def test_validation_message_blocks_continue_progress() -> None:
    body = (
        "Before you can continue with the application, please address "
        "the following issues: Cover letter - Please make a selection"
    )
    messages = detect_validation_messages(body)
    assert messages
    with pytest.raises(CoverLetterGateError, match="validation blocks"):
        assert_may_continue_documents_step(
            radio_checked=True,
            validation_messages=messages,
        )
    # Unchecked radio also blocks even without banner yet.
    with pytest.raises(CoverLetterGateError, match="not checked"):
        assert_may_continue_documents_step(
            radio_checked=False,
            validation_messages=(),
        )


def test_non_advancing_continue_stops_after_max_two_same_state_failures() -> None:
    guard = SameStateRetryGuard(max_failures=2)
    stuck = PageFingerprint(
        url="https://au.seek.com/job/1/apply",
        step_label="choose documents",
        validation_messages=("Cover letter - Please make a selection",),
    )
    assert guard.record(stuck, stuck) == "retry"
    assert guard.failures == 1
    assert guard.record(stuck, stuck) == "stop"
    assert guard.failures == 2


def test_successful_state_change_resets_same_state_failure_count() -> None:
    guard = SameStateRetryGuard(max_failures=2)
    choose = PageFingerprint(
        url="https://au.seek.com/job/1/apply",
        step_label="choose documents",
        validation_messages=(),
    )
    questions = PageFingerprint(
        url="https://au.seek.com/job/1/apply",
        step_label="answer employer questions",
        validation_messages=(),
    )
    assert guard.record(choose, choose) == "retry"
    assert guard.failures == 1
    assert state_advanced(choose, questions)
    assert guard.record(choose, questions) == "advanced"
    assert guard.failures == 0


def test_click_success_alone_is_not_progress_when_validation_present() -> None:
    before = fingerprint_from_text(
        url="https://au.seek.com/job/1/apply",
        body_text="Choose documents Continue",
    )
    after = fingerprint_from_text(
        url="https://au.seek.com/job/1/apply",
        body_text=(
            "Choose documents Cover letter - Please make a selection Continue"
        ),
    )
    assert not state_advanced(before, after)
