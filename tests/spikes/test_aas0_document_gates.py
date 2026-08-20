"""AAS-0.1 exact CV selection and Review document filename gates."""

from __future__ import annotations

import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.document_gates import (  # noqa: E402
    evaluate_cv_upload_wait_tick,
    evaluate_expected_cv_selection,
    evaluate_review_document_gate,
    filenames_equal,
    looks_like_resume_upload_busy,
    parse_review_document_filenames,
)
from aas0.resume_lifecycle import (  # noqa: E402
    application_cv_is_structural_default,
    build_seek_resume_snapshot,
    evaluate_default_change,
)
from aas0.session_handoff import build_final_review_handoff  # noqa: E402
from aas0.submit_guard import ControlClass, PageSignals, classify_control  # noqa: E402

NOVIGI_CV = "David Cropper - Novigi Pty Ltd - Senior AI Engineer - CV.pdf"
NOVIGI_CL = "David Cropper - Novigi Pty Ltd - Senior AI Engineer - Cover Letter.pdf"
REPURPOSE_CV = "David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf"
GENERAL_CV = "Candidate - Role CV.pdf"
EXPECTED_CV = "Candidate - Employer - Role - CV.pdf"
OTHER_CV = "Candidate - Other Co - Role - CV.pdf"
EXPECTED_CL = "Candidate - Employer - Role - Cover Letter.pdf"


def _snapshot(rows: list[tuple[str, bool]]):
    return build_seek_resume_snapshot(rows)


def test_expected_cv_selected_documents_step_may_proceed() -> None:
    snapshot = _snapshot(
        [
            (f"{EXPECTED_CV}\nAdded less than a minute ago", True),
            (f"{GENERAL_CV}\nDefault", False),
        ]
    )
    outcome = evaluate_expected_cv_selection(snapshot, EXPECTED_CV)
    assert outcome.should_stop is False
    assert outcome.selected is True
    assert outcome.reason == "expected_cv_selected"


def test_expected_cv_present_previous_selected_attempts_select() -> None:
    snapshot = _snapshot(
        [
            (f"{OTHER_CV}\nAdded 2 hours ago", True),
            (f"{EXPECTED_CV}\nAdded less than a minute ago", False),
        ]
    )
    waiting = evaluate_cv_upload_wait_tick(
        snapshot=snapshot,
        expected_filename=EXPECTED_CV,
        spinner_active=False,
        elapsed_ms=400,
        timeout_ms=15_000,
    )
    assert waiting.action == "attempt_select"
    selected = _snapshot(
        [
            (f"{OTHER_CV}\nAdded 2 hours ago", False),
            (f"{EXPECTED_CV}\nAdded less than a minute ago", True),
        ]
    )
    done = evaluate_cv_upload_wait_tick(
        snapshot=selected,
        expected_filename=EXPECTED_CV,
        spinner_active=False,
        elapsed_ms=800,
        timeout_ms=15_000,
    )
    assert done.action == "success"
    assert done.selected is True


def test_expected_cv_never_appears_stops() -> None:
    snapshot = _snapshot(
        [
            (f"{OTHER_CV}\nAdded 2 hours ago", True),
            (f"{GENERAL_CV}\nDefault", False),
        ]
    )
    outcome = evaluate_cv_upload_wait_tick(
        snapshot=snapshot,
        expected_filename=EXPECTED_CV,
        spinner_active=False,
        elapsed_ms=15_000,
        timeout_ms=15_000,
    )
    assert outcome.action == "stop"
    assert outcome.reason == "expected_cv_not_present"


def test_upload_spinner_remaining_stops() -> None:
    snapshot = _snapshot([(f"{OTHER_CV}", True)])
    outcome = evaluate_cv_upload_wait_tick(
        snapshot=snapshot,
        expected_filename=EXPECTED_CV,
        spinner_active=True,
        elapsed_ms=15_000,
        timeout_ms=15_000,
    )
    assert outcome.action == "stop"
    assert outcome.reason == "resume_upload_spinner_timeout"
    assert looks_like_resume_upload_busy(upload_button_aria_busy=True) is True
    continue_gate = evaluate_expected_cv_selection(
        snapshot, EXPECTED_CV, spinner_active=True
    )
    assert continue_gate.should_stop is True
    assert continue_gate.reason == "resume_upload_still_processing"


def test_repurpose_selected_while_novigi_expected_stops() -> None:
    snapshot = _snapshot(
        [
            (f"{REPURPOSE_CV}\nAdded about 2 hours ago", True),
            ("David Cropper - AI Engineer CV.pdf\nDefault", False),
        ]
    )
    outcome = evaluate_expected_cv_selection(snapshot, NOVIGI_CV)
    assert outcome.should_stop is True
    assert outcome.selected is False
    assert outcome.observed_selected == REPURPOSE_CV
    assert outcome.reason == "expected_cv_not_present"


def test_correct_cover_letter_does_not_excuse_wrong_cv() -> None:
    observation = parse_review_document_filenames(
        "Review and submit\nDocuments included\n"
        f"Résumé\n{REPURPOSE_CV}\n"
        f"Cover letter\n{NOVIGI_CL}\n"
        "Submit application\n"
    )
    assert observation.cover_letter_filename == NOVIGI_CL
    gate = evaluate_review_document_gate(
        expected_cv=NOVIGI_CV,
        expected_cover_letter=NOVIGI_CL,
        observation=observation,
    )
    assert gate.should_stop is True
    assert gate.allow_owner_handoff is False
    assert gate.reason == "review_cv_mismatch"


def test_final_review_matching_filenames_allows_handoff() -> None:
    observation = parse_review_document_filenames(
        "Documents included\n"
        f"Résumé\n{NOVIGI_CV}\n"
        f"Cover letter\n{NOVIGI_CL}\n"
        "Submit application\n"
    )
    gate = evaluate_review_document_gate(
        expected_cv=NOVIGI_CV,
        expected_cover_letter=NOVIGI_CL,
        observation=observation,
    )
    assert gate.should_stop is False
    assert gate.allow_owner_handoff is True
    assert gate.reason == "review_documents_match"


def test_final_review_repurpose_cv_novigi_cl_refuses_handoff() -> None:
    observation = parse_review_document_filenames(
        "Documents included\n"
        f"Resumé\n{REPURPOSE_CV}\n"
        f"Cover letter\n{NOVIGI_CL}\n"
        "Submit application\n"
    )
    gate = evaluate_review_document_gate(
        expected_cv=NOVIGI_CV,
        expected_cover_letter=NOVIGI_CL,
        observation=observation,
    )
    assert gate.allow_owner_handoff is False
    assert filenames_equal(gate.observed_cv, REPURPOSE_CV)


def test_review_document_filenames_unavailable_fail_closed() -> None:
    observation = parse_review_document_filenames(
        "Review and submit\nSubmit application\nCareer history"
    )
    assert observation.observable is False
    gate = evaluate_review_document_gate(
        expected_cv=NOVIGI_CV,
        expected_cover_letter=NOVIGI_CL,
        observation=observation,
    )
    assert gate.should_stop is True
    assert gate.reason == "review_documents_unobservable"


def test_handoff_still_never_clicks_submit() -> None:
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.submit_clicked_by_automation is False
    review = PageSignals(looks_like_review_or_confirmation=True)
    assert classify_control("Submit application", page=review) is ControlClass.FINAL_SUBMIT


def test_default_unchanged_wrong_application_cv_still_stops() -> None:
    before = _snapshot(
        [
            (f"{REPURPOSE_CV}", True),
            ("David Cropper - AI Engineer CV.pdf\nDefault", False),
        ]
    )
    after = _snapshot(
        [
            (f"{REPURPOSE_CV}", True),
            ("David Cropper - AI Engineer CV.pdf\nDefault", False),
        ]
    )
    change = evaluate_default_change(before, after)
    assert change.should_stop is False
    assert change.reason == "default_unchanged"
    cv_gate = evaluate_expected_cv_selection(after, NOVIGI_CV)
    assert cv_gate.should_stop is True
    assert cv_gate.reason == "expected_cv_not_present"


def test_expected_tailored_cv_cannot_be_accepted_structural_default() -> None:
    snapshot = _snapshot(
        [
            (f"{NOVIGI_CV}\nDefault", True),
            ("David Cropper - AI Engineer CV.pdf", False),
        ]
    )
    assert application_cv_is_structural_default(
        default_filename=snapshot.default_filename,
        expected_filename=NOVIGI_CV,
    )
    gate = evaluate_expected_cv_selection(snapshot, NOVIGI_CV)
    assert gate.selected is True
    generic = _snapshot(
        [
            (f"{NOVIGI_CV}", True),
            ("David Cropper - AI Engineer CV.pdf\nDefault", False),
        ]
    )
    assert not application_cv_is_structural_default(
        default_filename=generic.default_filename,
        expected_filename=NOVIGI_CV,
    )


def test_review_exact_filename_and_no_submit_remain_enforced() -> None:
    observation = parse_review_document_filenames(
        "Documents included\n"
        f"Résumé\n{NOVIGI_CV}\n"
        f"Cover letter\n{NOVIGI_CL}\n"
        "Submit application\n"
    )
    gate = evaluate_review_document_gate(
        expected_cv=NOVIGI_CV,
        expected_cover_letter=NOVIGI_CL,
        observation=observation,
    )
    assert gate.allow_owner_handoff is True
    wrong = parse_review_document_filenames(
        "Documents included\n"
        f"Résumé\n{REPURPOSE_CV}\n"
        f"Cover letter\n{NOVIGI_CL}\n"
        "Submit application\n"
    )
    mismatch = evaluate_review_document_gate(
        expected_cv=NOVIGI_CV,
        expected_cover_letter=NOVIGI_CL,
        observation=wrong,
    )
    assert mismatch.allow_owner_handoff is False
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.submit_clicked_by_automation is False
    page = PageSignals(looks_like_review_or_confirmation=True)
    assert classify_control("Submit application", page=page) is ControlClass.FINAL_SUBMIT
