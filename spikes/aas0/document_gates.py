"""Fail-closed CV selection and Review document filename gates (AAS-0.1).

Live Novigi 20260819T064132Z: ``set_input_files`` was treated as success while
SEEK kept a previous-opportunity résumé selected. These helpers compare exact
export filenames only. Default badge state is a separate invariant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .resume_lifecycle import SeekResumeSnapshot, extract_pdf_filename

CV_SELECTION_TIMEOUT_MS = 15_000

WaitAction = Literal["success", "keep_waiting", "attempt_select", "stop"]


class DocumentsStepGateError(RuntimeError):
    """Expected CV is not selected, or résumé upload is still processing."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class ReviewDocumentGateError(RuntimeError):
    """Review page does not show both expected export filenames."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class ExpectedCvSelectionOutcome:
    expected_filename: str
    present: bool
    selected: bool
    observed_selected: str | None
    should_attempt_select: bool
    should_stop: bool
    reason: str


@dataclass(frozen=True)
class CvUploadWaitDecision:
    action: WaitAction
    reason: str
    present: bool
    selected: bool
    observed_selected: str | None
    spinner_active: bool


@dataclass(frozen=True)
class ReviewDocumentObservation:
    resume_filename: str | None
    cover_letter_filename: str | None
    observable: bool


@dataclass(frozen=True)
class ReviewDocumentGate:
    should_stop: bool
    reason: str
    expected_cv: str
    expected_cover_letter: str
    observed_cv: str | None
    observed_cover_letter: str | None
    allow_owner_handoff: bool


def normalise_visible_filename(value: str | None) -> str:
    """Collapse DOM whitespace / zero-width characters; keep the filename identity."""
    text = (value or "").replace("\u2060", "").replace("\ufeff", "")
    text = text.replace("\\", "/").rsplit("/", 1)[-1]
    text = re.sub(r"\s+", " ", text).strip()
    return text


def filenames_equal(expected: str | None, observed: str | None) -> bool:
    left = normalise_visible_filename(expected)
    right = normalise_visible_filename(observed)
    if not left or not right:
        return False
    return left.casefold() == right.casefold()


def snapshot_has_filename(snapshot: SeekResumeSnapshot, expected: str) -> bool:
    return any(filenames_equal(expected, entry.filename) for entry in snapshot.entries)


def evaluate_expected_cv_selection(
    snapshot: SeekResumeSnapshot,
    expected_filename: str,
    *,
    spinner_active: bool = False,
) -> ExpectedCvSelectionOutcome:
    """Whether the application résumé radio is the expected export CV.

    Does not infer from Default, list position, or ``set_input_files``.
    """
    expected = normalise_visible_filename(expected_filename)
    observed = snapshot.selected_filename
    if not expected:
        return ExpectedCvSelectionOutcome(
            expected_filename="",
            present=False,
            selected=False,
            observed_selected=observed,
            should_attempt_select=False,
            should_stop=True,
            reason="expected_cv_filename_missing",
        )
    if spinner_active:
        return ExpectedCvSelectionOutcome(
            expected_filename=expected,
            present=snapshot_has_filename(snapshot, expected),
            selected=False,
            observed_selected=observed,
            should_attempt_select=False,
            should_stop=True,
            reason="resume_upload_still_processing",
        )
    present = snapshot_has_filename(snapshot, expected)
    selected = filenames_equal(expected, observed)
    if selected:
        return ExpectedCvSelectionOutcome(
            expected_filename=expected,
            present=present or True,
            selected=True,
            observed_selected=observed,
            should_attempt_select=False,
            should_stop=False,
            reason="expected_cv_selected",
        )
    if present and not selected:
        return ExpectedCvSelectionOutcome(
            expected_filename=expected,
            present=True,
            selected=False,
            observed_selected=observed,
            should_attempt_select=True,
            should_stop=True,
            reason="expected_cv_present_not_selected",
        )
    return ExpectedCvSelectionOutcome(
        expected_filename=expected,
        present=False,
        selected=False,
        observed_selected=observed,
        should_attempt_select=False,
        should_stop=True,
        reason="expected_cv_not_present",
    )


def evaluate_cv_upload_wait_tick(
    *,
    snapshot: SeekResumeSnapshot,
    expected_filename: str,
    spinner_active: bool,
    elapsed_ms: int,
    timeout_ms: int = CV_SELECTION_TIMEOUT_MS,
) -> CvUploadWaitDecision:
    """One poll of post-upload CV appearance / selection / spinner."""
    expected = normalise_visible_filename(expected_filename)
    present = snapshot_has_filename(snapshot, expected) if expected else False
    selected = filenames_equal(expected, snapshot.selected_filename)
    observed = snapshot.selected_filename
    timed_out = elapsed_ms >= timeout_ms

    if not expected:
        return CvUploadWaitDecision(
            action="stop",
            reason="expected_cv_filename_missing",
            present=False,
            selected=False,
            observed_selected=observed,
            spinner_active=spinner_active,
        )
    if timed_out:
        if spinner_active:
            return CvUploadWaitDecision(
                action="stop",
                reason="resume_upload_spinner_timeout",
                present=present,
                selected=selected,
                observed_selected=observed,
                spinner_active=True,
            )
        if selected:
            return CvUploadWaitDecision(
                action="success",
                reason="expected_cv_selected",
                present=True,
                selected=True,
                observed_selected=observed,
                spinner_active=False,
            )
        if not present:
            return CvUploadWaitDecision(
                action="stop",
                reason="expected_cv_not_present",
                present=False,
                selected=False,
                observed_selected=observed,
                spinner_active=False,
            )
        return CvUploadWaitDecision(
            action="stop",
            reason="expected_cv_present_not_selected",
            present=True,
            selected=False,
            observed_selected=observed,
            spinner_active=False,
        )
    if spinner_active:
        return CvUploadWaitDecision(
            action="keep_waiting",
            reason="resume_upload_processing",
            present=present,
            selected=selected,
            observed_selected=observed,
            spinner_active=True,
        )
    if selected:
        return CvUploadWaitDecision(
            action="success",
            reason="expected_cv_selected",
            present=True,
            selected=True,
            observed_selected=observed,
            spinner_active=False,
        )
    if present and not selected:
        return CvUploadWaitDecision(
            action="attempt_select",
            reason="expected_cv_present_not_selected",
            present=True,
            selected=False,
            observed_selected=observed,
            spinner_active=False,
        )
    return CvUploadWaitDecision(
        action="keep_waiting",
        reason="expected_cv_not_present_yet",
        present=False,
        selected=False,
        observed_selected=observed,
        spinner_active=False,
    )


def looks_like_resume_upload_busy(
    *,
    upload_button_aria_busy: bool = False,
    upload_control_has_progress: bool = False,
    uploading_text_visible: bool = False,
) -> bool:
    return bool(
        upload_button_aria_busy
        or upload_control_has_progress
        or uploading_text_visible
    )


def _filename_after_label(text: str, label_pattern: str) -> str | None:
    pattern = re.compile(
        rf"{label_pattern}\s*[:\-]?\s*(?:\r?\n)?\s*([^\n\r]+\.pdf)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    raw = match.group(1).strip()
    return extract_pdf_filename(raw) or normalise_visible_filename(raw) or None


def parse_review_document_filenames(body_text: str) -> ReviewDocumentObservation:
    """Read Résumé / Cover letter PDF names from SEEK Review copy.

    Exact filename tokens only. Does not fuzzy-match company or role.
    """
    text = body_text or ""
    window = text
    lowered = text.casefold()
    marker = lowered.find("documents included")
    if marker >= 0:
        window = text[marker:]
    resume = _filename_after_label(window, r"r[eé]sum[eé]")
    cover = _filename_after_label(window, r"cover letter")
    return ReviewDocumentObservation(
        resume_filename=resume,
        cover_letter_filename=cover,
        observable=bool(resume and cover),
    )


def evaluate_review_document_gate(
    *,
    expected_cv: str,
    expected_cover_letter: str,
    observation: ReviewDocumentObservation,
) -> ReviewDocumentGate:
    """Mandatory fail-closed check before APPLICATION READY FOR OWNER."""
    expected_cv_n = normalise_visible_filename(expected_cv)
    expected_cl_n = normalise_visible_filename(expected_cover_letter)
    observed_cv = observation.resume_filename
    observed_cl = observation.cover_letter_filename
    if not expected_cv_n or not expected_cl_n:
        return ReviewDocumentGate(
            should_stop=True,
            reason="expected_filenames_unavailable",
            expected_cv=expected_cv_n,
            expected_cover_letter=expected_cl_n,
            observed_cv=observed_cv,
            observed_cover_letter=observed_cl,
            allow_owner_handoff=False,
        )
    if not observation.observable:
        return ReviewDocumentGate(
            should_stop=True,
            reason="review_documents_unobservable",
            expected_cv=expected_cv_n,
            expected_cover_letter=expected_cl_n,
            observed_cv=observed_cv,
            observed_cover_letter=observed_cl,
            allow_owner_handoff=False,
        )
    cv_ok = filenames_equal(expected_cv_n, observed_cv)
    cl_ok = filenames_equal(expected_cl_n, observed_cl)
    if cv_ok and cl_ok:
        return ReviewDocumentGate(
            should_stop=False,
            reason="review_documents_match",
            expected_cv=expected_cv_n,
            expected_cover_letter=expected_cl_n,
            observed_cv=observed_cv,
            observed_cover_letter=observed_cl,
            allow_owner_handoff=True,
        )
    if not cv_ok and cl_ok:
        reason = "review_cv_mismatch"
    elif cv_ok and not cl_ok:
        reason = "review_cover_letter_mismatch"
    else:
        reason = "review_document_mismatch"
    return ReviewDocumentGate(
        should_stop=True,
        reason=reason,
        expected_cv=expected_cv_n,
        expected_cover_letter=expected_cl_n,
        observed_cv=observed_cv,
        observed_cover_letter=observed_cl,
        allow_owner_handoff=False,
    )
