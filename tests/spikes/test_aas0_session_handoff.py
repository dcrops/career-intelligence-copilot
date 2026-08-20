"""Tests for AAS final-review handoff, submission observation, CV rotation class."""

from __future__ import annotations

import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.metrics import SpikeMetrics  # noqa: E402
from aas0.session_handoff import (  # noqa: E402
    CvRotationClass,
    apply_owner_session_submission_observation,
    build_final_review_handoff,
    classify_seek_cv_for_rotation,
    looks_like_final_submit_label,
    may_auto_delete_seek_cv,
    observe_submission_from_page_text,
    propose_external_export_filename,
)


def test_final_review_handoff_keeps_browser_open_and_never_submits() -> None:
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.automation_stopped is True
    assert handoff.browser_kept_open_for_owner is True
    assert handoff.submit_clicked_by_automation is False
    assert handoff.final_submit_control_visible is True


def test_submit_application_label_detected() -> None:
    assert looks_like_final_submit_label("Submit application")
    assert looks_like_final_submit_label("Submit application\u2060")
    assert not looks_like_final_submit_label("Continue")


def test_observe_submission_success_and_not_completed() -> None:
    ok = observe_submission_from_page_text(
        "Thank you for applying. Your application has been submitted."
    )
    assert ok.status == "likely_submitted"
    assert ok.observed is True
    pending = observe_submission_from_page_text(
        "Review and submit  Submit application"
    )
    assert pending.status == "not_completed"
    assert pending.observed is False


def test_observe_submission_apply_success_url() -> None:
    result = observe_submission_from_page_text(
        "Good luck, David",
        url="https://www.seek.com.au/job/93837541/apply/success",
    )
    assert result.status == "likely_submitted"
    assert result.evidence == "apply_success_url"


def test_observe_submission_application_has_been_sent() -> None:
    result = observe_submission_from_page_text(
        "Your application has been sent to Example Pty Ltd"
    )
    assert result.status == "likely_submitted"
    assert result.evidence == "application has been sent"


def test_observe_submission_unrelated_page_unknown() -> None:
    result = observe_submission_from_page_text(
        "Search jobs. You might also like these roles."
    )
    assert result.status == "unknown"
    assert result.evidence == "no_clear_submission_signal"


def test_observe_submission_review_page_is_not_submitted() -> None:
    result = observe_submission_from_page_text(
        "Review and submit\nDocuments included\nSubmit application",
        url="https://www.seek.com.au/job/93837541/apply",
    )
    assert result.status == "not_completed"
    assert result.observed is False


def test_cv_rotation_protects_default_only() -> None:
    assert (
        classify_seek_cv_for_rotation("opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf")
        is CvRotationClass.DISPOSABLE
    )
    assert may_auto_delete_seek_cv("opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf")
    assert classify_seek_cv_for_rotation("David Cropper CV.pdf") is CvRotationClass.DISPOSABLE
    assert may_auto_delete_seek_cv("David Cropper CV.pdf")
    assert (
        classify_seek_cv_for_rotation(
            "David Cropper Attribute Group AI Deployment Engineer CV.pdf"
        )
        is CvRotationClass.DISPOSABLE
    )
    assert may_auto_delete_seek_cv(
        "David Cropper Attribute Group AI Deployment Engineer CV.pdf"
    )
    assert (
        classify_seek_cv_for_rotation("David Cropper - AI Engineer CV.pdf", is_default=True)
        is CvRotationClass.PROTECT
    )
    assert not may_auto_delete_seek_cv(
        "David Cropper - AI Engineer CV.pdf", is_default=True
    )


def test_external_export_filename_hides_opportunity_id() -> None:
    name = propose_external_export_filename(
        full_name="David Cropper",
        company="Repurpose It",
        title="AI Engineer",
        kind="cv",
    )
    assert name == "David_Cropper_Repurpose_It_AI_Engineer_CV.pdf"
    assert "opp_" not in name
    cl = propose_external_export_filename(
        full_name="David Cropper",
        company="Repurpose It",
        title="AI Engineer",
        kind="cover_letter",
    )
    assert cl == "David_Cropper_Repurpose_It_AI_Engineer_Cover_Letter.pdf"


def test_owner_session_teardown_records_hatch_success_without_submit_click() -> None:
    metrics = SpikeMetrics(opportunity_id="opp_01M0CTP2ZJ754YG5G7YA7X3ZMA")
    metrics.application_submission = "not_completed"
    metrics.submit_clicked = False
    observation = apply_owner_session_submission_observation(
        metrics,
        body_text="Nice work, David. Your application has been sent to Hatch",
        url="https://www.seek.com.au/job/94075152/apply/success",
    )
    assert observation.status == "likely_submitted"
    assert metrics.application_submission == "likely_submitted"
    assert metrics.submit_clicked is False


def test_owner_session_teardown_does_not_infer_submit_from_ending_alone() -> None:
    metrics = SpikeMetrics(opportunity_id="opp_01M0CTP2ZJ754YG5G7YA7X3ZMA")
    observation = apply_owner_session_submission_observation(
        metrics,
        body_text="Answer employer questions\nContinue",
        url="https://www.seek.com.au/job/94075152/apply",
    )
    assert observation.status == "unknown"
    assert metrics.application_submission == "unknown"
    assert metrics.submit_clicked is False
