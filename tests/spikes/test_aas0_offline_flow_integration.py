"""Offline whole-flow AAS-0.1 integration (no SEEK, no Playwright browser).

Sequences the current orchestration helpers in the same order as run_assist.
The fake is only the SEEK DOM/browser boundary.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.answer_policy import AnswerDecision, KnownAnswers, resolve_answer  # noqa: E402
from aas0.document_gates import (  # noqa: E402
    DocumentsStepGateError,
    evaluate_cv_upload_wait_tick,
    evaluate_expected_cv_selection,
    evaluate_review_document_gate,
    parse_review_document_filenames,
)
from aas0.metrics import SpikeMetrics  # noqa: E402
from aas0.resume_lifecycle import (  # noqa: E402
    build_seek_resume_snapshot,
    evaluate_default_checkbox_guard,
    extract_pdf_filename,
    looks_like_cover_letter_pdf_filename,
    row_is_structurally_default,
    should_skip_resume_radio_row,
)
from aas0.resume_rotation import (  # noqa: E402
    SEEK_RESUME_DELETE_ACTION,
    SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
    SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
    SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
    SEEK_RESUME_DELETE_CONFIRMATION_PROMPT,
    ResumeRowMenu,
    build_delete_confirmation_observation,
    empty_delete_confirmation_observation,
    evaluate_rotation_decision,
    perform_one_resume_deletion,
    skips_as_metrics,
    wait_until_deletion_verified,
)
from aas0.seek_documents import (  # noqa: E402
    COVER_LETTER_UPLOAD_LABEL,
    choose_documents_visible,
    documents_step_ready_to_continue,
    record_resume_snapshot,
    should_run_documents_stage,
)
from aas0.session_handoff import (  # noqa: E402
    apply_owner_session_submission_observation,
    build_final_review_handoff,
    observe_submission_from_page_text,
)
from aas0.state_progress import (  # noqa: E402
    fingerprint_from_text,
    infer_step_label,
    is_final_review_page,
    looks_like_stepper_review_label,
    state_advanced,
)
from aas0.submit_guard import (  # noqa: E402
    ControlClass,
    FinalSubmitGuardError,
    PageSignals,
    assert_may_activate,
    classify_control,
)
from aas0.upload_artefacts import (  # noqa: E402
    is_internal_opp_pdf_filename,
    validate_external_upload_pdf,
)

OPP_ID = "opp_01KZQK08P757DCAE1RM5GPPKC6"
G360_CV = "David Cropper - Global 360 - AI Engineer - Applied - CV.pdf"
G360_CL = "David Cropper - Global 360 - AI Engineer - Applied - Cover Letter.pdf"
PROTECTED_DEFAULT = "David Cropper - AI Engineer CV.pdf"
NOVIGI_CV = "David Cropper - Novigi Pty Ltd - Senior AI Engineer - CV.pdf"
REPURPOSE_CV = "David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf"
ATTR_CV = "David Cropper Attribute Group AI Deployment Engineer CV.pdf"
EXPORT_DIR = (
    Path("data")
    / "application_packages"
    / OPP_ID
    / "export"
)

QUESTIONS_BODY = (
    "Answer employer questions\n"
    "Review and submit\n"
    "Full name\n"
    "Why are you interested in this role?\n"
    "Continue\n"
)
PROFILE_BODY = "Update SEEK Profile\nReview and submit\nContinue\n"
REVIEW_TEMPLATE = (
    "Review and submit\n"
    "Documents included\n"
    "Résumé\n"
    "{cv}\n"
    "Cover letter\n"
    "{cl}\n"
    "Submit application\n"
)
SUCCESS_BODY = "Your application has been sent to Global 360"
HATCH_OPP = "opp_01M0CTP2ZJ754YG5G7YA7X3ZMA"
HATCH_CV = "David Cropper - Hatch - AI Trainer - CV.pdf"
HATCH_CL = "David Cropper - Hatch - AI Trainer - Cover Letter.pdf"
HATCH_STEPPER = (
    "Choose documents\n"
    "Answer employer questions\n"
    "Update SEEK Profile\n"
    "Review and submit\n"
)
HATCH_DOCUMENTS_BODY = (
    HATCH_STEPPER
    + "Make this my default résumé\n"
    + "Don't include a résumé\n"
    + "Upload a cover letter\n"
    + f"{HATCH_CV}\nDefault\n{PROTECTED_DEFAULT}\n"
)
HATCH_QUESTIONS_BODY = (
    HATCH_STEPPER
    + "Which of the following statements best describes your right to work in Australia?\n"
    + "Continue\n"
)
HATCH_PROFILE_BODY = HATCH_STEPPER + "Update SEEK Profile heading\nContinue\n"
HATCH_SUCCESS_BODY = "Your application has been sent to Hatch"


class _BodyLocator:
    def __init__(self, text: str) -> None:
        self._text = text

    def inner_text(self, timeout: int = 0) -> str:  # noqa: ARG002
        return self._text


class _RadioLocator:
    def __init__(self, *, count: int, checked: bool) -> None:
        self._count = count
        self._checked = checked
        self.first = self

    def count(self) -> int:
        return self._count

    def is_checked(self) -> bool:
        return self._checked


class FakeSeekPage:
    """Browser-boundary fake. Does not launch Playwright or contact SEEK."""

    def __init__(
        self,
        *,
        body: str,
        url: str = "https://www.seek.com.au/job/1/apply",
        cover_letter_radio_present: bool = True,
        cover_letter_radio_checked: bool = True,
        resume_file_count: int = 0,
        cover_file_count: int = 0,
        default_checkbox: bool = False,
    ) -> None:
        self.body = body
        self.url = url
        self.cover_letter_radio_present = cover_letter_radio_present
        self.cover_letter_radio_checked = cover_letter_radio_checked
        self.resume_file_count = resume_file_count
        self.cover_file_count = cover_file_count
        self.default_checkbox = default_checkbox
        self.submit_clicked = False

    def locator(self, selector: str):
        if selector == "body":
            return _BodyLocator(self.body)
        lowered = selector.lower()
        if "cover" in lowered:
            return _RadioLocator(count=self.cover_file_count, checked=False)
        if "resume" in lowered:
            return _RadioLocator(count=self.resume_file_count, checked=False)
        return _RadioLocator(count=0, checked=False)

    def get_by_role(self, role: str, name=None):
        if role == "checkbox":
            return _RadioLocator(
                count=1 if self.default_checkbox else 0,
                checked=False,
            )
        if role == "radio" and name == COVER_LETTER_UPLOAD_LABEL:
            return _RadioLocator(
                count=1 if self.cover_letter_radio_present else 0,
                checked=self.cover_letter_radio_checked,
            )
        return _RadioLocator(count=0, checked=False)


class OfflineDeleteDriver:
    """Row-scoped Delete driver over in-memory SEEK radios."""

    def __init__(
        self,
        radio_rows: list[tuple[str, bool]],
        *,
        confirmation_before: bool = False,
        confirmation_after_click: bool = False,
        delete_settles_after_polls: int = 0,
        delete_wrong_row: bool = False,
        move_default_on_poll: int | None = None,
    ) -> None:
        self.radio_rows = radio_rows
        self.opened: list[int] = []
        self.clicked: list[str] = []
        self.confirmation_clicked: list[str] = []
        self.cancel_clicked: list[str] = []
        self.close_clicked: list[str] = []
        self.dismiss_clicked: list[str] = []
        self._confirm = confirmation_before
        self.confirmation_after_click = confirmation_after_click
        self._opened_index: int | None = None
        self.delete_settles_after_polls = delete_settles_after_polls
        self.delete_wrong_row = delete_wrong_row
        self.move_default_on_poll = move_default_on_poll
        self._pending_delete_index: int | None = None
        self._verification_polls = 0
        self.delete_apply_count = 0

    def confirmation_dialog_visible(self) -> bool:
        return self._confirm

    def _opened_filename(self) -> str | None:
        if self._opened_index is None:
            return None
        visible_index = 0
        for text, _selected in self.radio_rows:
            if should_skip_resume_radio_row(text) or not extract_pdf_filename(text):
                visible_index += 1
                continue
            if visible_index == self._opened_index:
                return extract_pdf_filename(text)
            visible_index += 1
        return None

    def observe_delete_confirmation(self, candidate_filename: str | None = None):
        if not self._confirm:
            return empty_delete_confirmation_observation()
        opened = self._opened_filename()
        if self.confirmation_after_click:
            return build_delete_confirmation_observation(
                dialog_count=1,
                dialog_text="Please confirm.\nDelete\nCancel",
                candidate_filename=candidate_filename,
            action_names=(
                SEEK_RESUME_DELETE_ACTION,
                SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
                SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
            ),
        )
        return build_delete_confirmation_observation(
            dialog_count=1,
            dialog_text=(
                f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{opened}\n"
                "\u2060Delete\nCancel"
            ),
            candidate_filename=candidate_filename,
            action_names=(
                "\u2060Delete",
                SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
                SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
            ),
        )

    def row_menus(self) -> tuple[ResumeRowMenu, ...]:
        menus: list[ResumeRowMenu] = []
        visible_index = 0
        for text, _selected in self.radio_rows:
            if should_skip_resume_radio_row(text) or not extract_pdf_filename(text):
                visible_index += 1
                continue
            filename = extract_pdf_filename(text) or ""
            opened = self._opened_index == visible_index
            menus.append(
                ResumeRowMenu(
                    filename=filename,
                    index=visible_index,
                    is_default=row_is_structurally_default(text),
                    overflow_control_count=1,
                    menu_open=opened,
                    menu_actions=(
                        ("Download", SEEK_RESUME_DELETE_ACTION) if opened else ()
                    ),
                )
            )
            visible_index += 1
        return tuple(menus)

    def open_overflow(self, row_index: int) -> str:
        self.opened.append(row_index)
        self._opened_index = row_index
        return "opened"

    def click_exact_delete(self) -> str:
        self.clicked.append(SEEK_RESUME_DELETE_ACTION)
        self._confirm = True
        return "clicked"

    def click_confirmation_delete(self) -> str:
        if self.confirmation_after_click:
            return "resume_delete_confirmation_unobserved"
        self.confirmation_clicked.append(SEEK_RESUME_DELETE_ACTION)
        self._confirm = False
        if self._opened_index is not None:
            self._pending_delete_index = self._opened_index
        if self.delete_settles_after_polls <= 0:
            self._apply_pending_delete()
        self._opened_index = None
        return "clicked"

    def _move_default_to_novigi(self) -> None:
        mutated: list[tuple[str, bool]] = []
        for text, selected in self.radio_rows:
            filename = extract_pdf_filename(text)
            if filename == PROTECTED_DEFAULT:
                mutated.append((f"{PROTECTED_DEFAULT}\nAdded 30 days ago", False))
            elif filename == NOVIGI_CV:
                mutated.append((f"{NOVIGI_CV}\nDefault\nAdded 41 minutes ago", True))
            else:
                mutated.append((text, selected))
        self.radio_rows = mutated

    def _apply_pending_delete(self) -> None:
        if self._pending_delete_index is None:
            return
        index = self._pending_delete_index
        if self.delete_wrong_row:
            for row_index, (text, _selected) in enumerate(self.radio_rows):
                if extract_pdf_filename(text) == NOVIGI_CV:
                    index = row_index
                    break
        if 0 <= index < len(self.radio_rows):
            del self.radio_rows[index]
            self.delete_apply_count += 1
        self._pending_delete_index = None

    def observe_for_verification(self):
        self._verification_polls += 1
        if (
            self.move_default_on_poll is not None
            and self._verification_polls == self.move_default_on_poll
        ):
            self._move_default_to_novigi()
        if (
            self._pending_delete_index is not None
            and self.delete_settles_after_polls > 0
            and self._verification_polls >= self.delete_settles_after_polls
        ):
            self._apply_pending_delete()
        return build_seek_resume_snapshot(self.radio_rows)


def _initial_choose_documents_rows() -> list[tuple[str, bool]]:
    """Newest-first saved CVs + cover-letter controls (live Global 360 shape)."""
    return [
        (f"{PROTECTED_DEFAULT}\nDefault\nAdded 30 days ago", False),
        (f"{NOVIGI_CV}\nAdded 41 minutes ago", True),
        (f"{REPURPOSE_CV}\nAdded 7 days ago", False),
        (f"{ATTR_CV}", False),
        (f"{ATTR_CV}", False),
        ("Don't include a résumé", False),
        (G360_CL, False),
        (f"Upload a cover letter\n{G360_CL}", False),
        ("Write a cover letter", False),
    ]


def _choose_documents_body(rows: list[tuple[str, bool]]) -> str:
    blob = "\n".join(text for text, _selected in rows)
    return f"Choose documents\n{blob}\nUpload\n"


@dataclass
class OfflineFlowResult:
    outcome: str
    stage: str
    metrics: SpikeMetrics
    application_ready: bool
    submit_clicked: bool
    rotation_deletes: int
    candidate_filename: str | None = None
    notes: list[str] = field(default_factory=list)


def _preflight(metrics: SpikeMetrics) -> None:
    cv_path = EXPORT_DIR / G360_CV
    cl_path = EXPORT_DIR / G360_CL
    assert validate_external_upload_pdf(cv_path, kind="cv") is None
    assert validate_external_upload_pdf(cl_path, kind="cover_letter") is None
    assert not is_internal_opp_pdf_filename(G360_CV)
    assert not is_internal_opp_pdf_filename(G360_CL)
    metrics.expected_cv_filename = G360_CV
    metrics.expected_cover_letter_filename = G360_CL
    metrics.add_note("preflight_ok truth.external_use_allowed=True")


def _assert_inventory_is_saved_resumes_only(snapshot) -> None:
    names = [entry.filename for entry in snapshot.entries]
    assert G360_CL not in names
    assert all(not looks_like_cover_letter_pdf_filename(name) for name in names)
    assert PROTECTED_DEFAULT in names
    assert NOVIGI_CV in names
    assert ATTR_CV in names


def run_offline_aas_flow(
    *,
    confirmation_before: bool = False,
    confirmation_after_click: bool = False,
    move_default_after_delete: bool = False,
    retry_selected_filename: str = G360_CV,
    include_expected_cv_on_retry: bool = True,
    review_cv: str = G360_CV,
    review_cl: str = G360_CL,
    early_stop_before_rotation: bool = False,
    delete_settles_after_polls: int = 3,
    delete_wrong_row: bool = False,
    verification_timeout_ms: int = 15_000,
    verification_poll_ms: int = 400,
) -> OfflineFlowResult:
    """Compose current AAS helpers. Does not launch SEEK or Playwright."""
    metrics = SpikeMetrics(opportunity_id=OPP_ID)
    _preflight(metrics)
    if early_stop_before_rotation:
        metrics.final_stage_reached = "stopped_cv_selection"
        metrics.add_failure("early_stop_before_rotation")
        metrics.submit_clicked = False
        metrics.application_submission = "not_completed"
        return OfflineFlowResult(
            outcome="stop",
            stage="stopped_cv_selection",
            metrics=metrics,
            application_ready=False,
            submit_clicked=False,
            rotation_deletes=0,
        )

    radio_rows = _initial_choose_documents_rows()
    initial = build_seek_resume_snapshot(radio_rows)
    record_resume_snapshot(metrics, initial, stage="before")
    _assert_inventory_is_saved_resumes_only(initial)
    assert initial.default_filename == PROTECTED_DEFAULT
    assert initial.selected_filename == NOVIGI_CV
    assert not any(entry.filename == G360_CV for entry in initial.entries)

    first_wait = evaluate_cv_upload_wait_tick(
        snapshot=initial,
        expected_filename=G360_CV,
        spinner_active=True,
        elapsed_ms=15_000,
    )
    assert first_wait.action == "stop"
    metrics.upload_failure_reason = first_wait.reason
    metrics.cv_selection_reason = first_wait.reason

    decision = evaluate_rotation_decision(
        entries=initial.entries,
        upload_failure_reason=first_wait.reason,
        rotation_already_attempted=False,
        default_observable_before=initial.default_observable,
    )
    metrics.resume_rotation_reason = decision.reason
    metrics.cleanup_candidate = decision.candidate.filename
    metrics.cleanup_candidate_reason = decision.candidate.reason
    metrics.cleanup_skips = skips_as_metrics(decision.skips)
    metrics.resume_rotation_attempted = True
    metrics.resume_default_before_deletion = initial.default_filename
    if decision.action != "attempt_delete":
        metrics.final_stage_reached = "stopped_cv_selection"
        metrics.submit_clicked = False
        return OfflineFlowResult(
            outcome="stop",
            stage="stopped_cv_selection",
            metrics=metrics,
            application_ready=False,
            submit_clicked=False,
            rotation_deletes=0,
            candidate_filename=decision.candidate.filename,
        )

    driver = OfflineDeleteDriver(
        radio_rows,
        confirmation_before=confirmation_before,
        confirmation_after_click=confirmation_after_click,
        delete_settles_after_polls=delete_settles_after_polls,
        delete_wrong_row=delete_wrong_row,
        move_default_on_poll=1 if move_default_after_delete else None,
    )
    deletion_status = perform_one_resume_deletion(
        driver,
        candidate_filename=decision.candidate.filename,
        candidate_index=decision.candidate.index,
    )
    if deletion_status == "resume_delete_confirmation_unobserved":
        metrics.resume_rotation_reason = deletion_status
        metrics.final_stage_reached = "stopped_cv_selection"
        metrics.submit_clicked = False
        metrics.add_failure(deletion_status)
        return OfflineFlowResult(
            outcome="stop",
            stage="stopped_cv_selection",
            metrics=metrics,
            application_ready=False,
            submit_clicked=False,
            rotation_deletes=0,
            candidate_filename=decision.candidate.filename,
        )
    if deletion_status != "clicked_delete":
        metrics.final_stage_reached = "stopped_cv_selection"
        metrics.submit_clicked = False
        metrics.add_failure(deletion_status)
        return OfflineFlowResult(
            outcome="stop",
            stage="stopped_cv_selection",
            metrics=metrics,
            application_ready=False,
            submit_clicked=False,
            rotation_deletes=0,
            candidate_filename=decision.candidate.filename,
        )
    assert driver.confirmation_clicked == [SEEK_RESUME_DELETE_ACTION]
    assert driver.cancel_clicked == []
    assert driver.close_clicked == []
    assert driver.dismiss_clicked == []
    assert SEEK_RESUME_DELETE_CONFIRMATION_CLOSE not in driver.clicked
    assert SEEK_RESUME_DELETE_CONFIRMATION_CANCEL not in driver.clicked
    assert SEEK_RESUME_DELETE_CONFIRMATION_DISMISS not in driver.clicked

    metrics.resume_list_count_before = len(initial.entries)
    metrics.resume_deleted_filename = decision.candidate.filename
    waited = wait_until_deletion_verified(
        driver.observe_for_verification,
        before=initial,
        deleted_filename=decision.candidate.filename or "",
        deleted_index=decision.candidate.index,
        timeout_ms=verification_timeout_ms,
        poll_ms=verification_poll_ms,
        wait=lambda _ms: None,
    )
    after_delete = waited.snapshot
    record_resume_snapshot(metrics, after_delete, stage="after_upload")
    metrics.resume_default_after_deletion = after_delete.default_filename
    metrics.resume_delete_verification_poll_count = waited.poll_count
    metrics.resume_delete_verification_wait_ms = waited.elapsed_ms
    metrics.resume_delete_verification_reason = waited.reason
    metrics.resume_list_count_after_deletion = len(after_delete.entries)
    if waited.action != "verified":
        metrics.resume_rotation_reason = waited.reason
        metrics.final_stage_reached = "stopped_cv_selection"
        metrics.submit_clicked = False
        metrics.add_failure(waited.reason)
        if waited.reason == "default_changed_after_deletion":
            metrics.default_changed_unexpected = True
            metrics.default_change_reason = waited.reason
        return OfflineFlowResult(
            outcome="stop",
            stage="stopped_cv_selection",
            metrics=metrics,
            application_ready=False,
            submit_clicked=False,
            rotation_deletes=driver.delete_apply_count,
            candidate_filename=decision.candidate.filename,
        )

    retry_rows: list[tuple[str, bool]] = []
    if include_expected_cv_on_retry:
        retry_rows.append(
            (
                f"{G360_CV}\nAdded less than a minute ago",
                retry_selected_filename == G360_CV,
            )
        )
    for text, selected in driver.radio_rows:
        filename = extract_pdf_filename(text)
        if filename == G360_CV:
            continue
        if filename == retry_selected_filename and retry_selected_filename != G360_CV:
            retry_rows.append((text, True))
        elif filename == NOVIGI_CV and retry_selected_filename != NOVIGI_CV:
            retry_rows.append((text, False))
        else:
            retry_rows.append((text, selected and filename == retry_selected_filename))
    retry_snapshot = build_seek_resume_snapshot(retry_rows)
    record_resume_snapshot(metrics, retry_snapshot, stage="after_upload")
    metrics.resume_rotation_retry_attempted = True
    retry_wait = evaluate_cv_upload_wait_tick(
        snapshot=retry_snapshot,
        expected_filename=G360_CV,
        spinner_active=False,
        elapsed_ms=15_000,
    )
    retry_selected = retry_wait.action != "stop" and retry_wait.selected
    metrics.resume_rotation_retry_outcome = retry_wait.reason
    metrics.cv_selection_reason = retry_wait.reason
    metrics.expected_cv_selected = retry_selected
    metrics.selected_resume_after_upload = retry_snapshot.selected_filename
    if not retry_selected:
        metrics.resume_rotation_reason = "retry_failed_no_second_deletion"
        metrics.final_stage_reached = "stopped_cv_selection"
        metrics.submit_clicked = False
        metrics.add_failure("retry_failed_no_second_deletion")
        second = evaluate_rotation_decision(
            entries=retry_snapshot.entries,
            upload_failure_reason=retry_wait.reason,
            rotation_already_attempted=True,
            retry_attempted=True,
            retry_expected_cv_selected=False,
            default_observable_before=retry_snapshot.default_observable,
        )
        assert second.action == "stop"
        return OfflineFlowResult(
            outcome="stop",
            stage="stopped_cv_selection",
            metrics=metrics,
            application_ready=False,
            submit_clicked=False,
            rotation_deletes=1,
            candidate_filename=decision.candidate.filename,
        )

    metrics.resume_rotation_reason = "retry_expected_cv_selected"
    checkbox = evaluate_default_checkbox_guard(
        present=True,
        was_checked=True,
        still_checked=False,
        uncheck_attempted=True,
    )
    metrics.default_checkbox_reason = checkbox.reason
    assert checkbox.should_stop is False

    page = FakeSeekPage(
        body=_choose_documents_body(retry_rows),
        cover_letter_radio_present=True,
        cover_letter_radio_checked=True,
    )
    documents_step_ready_to_continue(
        page,
        expected_cv_filename=G360_CV,
        snapshot=retry_snapshot,
        spinner_active=False,
    )

    questions = fingerprint_from_text(
        url="https://www.seek.com.au/job/1/apply",
        body_text=QUESTIONS_BODY,
    )
    profile = fingerprint_from_text(
        url="https://www.seek.com.au/job/1/apply",
        body_text=PROFILE_BODY,
    )
    assert questions.step_label == "answer employer questions"
    assert profile.step_label == "update seek profile"
    assert looks_like_stepper_review_label("Review and submit")
    assert is_final_review_page(QUESTIONS_BODY) is False
    assert is_final_review_page(PROFILE_BODY) is False
    assert state_advanced(
        fingerprint_from_text(url="", body_text="Choose documents"),
        questions,
    )
    known = KnownAnswers(full_name="David Cropper")
    assert resolve_answer("Full name", known).decision is AnswerDecision.KNOWN
    assert resolve_answer("Why are you interested in this role?", known).decision is (
        AnswerDecision.PAUSE
    )
    form_signals = PageSignals(
        url="https://www.seek.com.au/job/1/apply",
        looks_like_application_form=True,
        looks_like_review_or_confirmation=False,
    )
    assert classify_control("Continue", page=form_signals) is ControlClass.NAVIGATION
    assert_may_activate("Continue", page=form_signals)

    review_body = REVIEW_TEMPLATE.format(cv=review_cv, cl=review_cl)
    review_page = FakeSeekPage(
        body=review_body,
        url="https://www.seek.com.au/job/1/apply",
    )
    assert is_final_review_page(review_body) is True
    observation = parse_review_document_filenames(review_body)
    gate = evaluate_review_document_gate(
        expected_cv=G360_CV,
        expected_cover_letter=G360_CL,
        observation=observation,
    )
    metrics.record_review_document_gate(
        observed_cv=gate.observed_cv,
        observed_cover_letter=gate.observed_cover_letter,
        reason=gate.reason,
    )
    if gate.should_stop or not gate.allow_owner_handoff:
        metrics.final_stage_reached = "stopped_review_documents"
        metrics.submit_clicked = False
        metrics.application_submission = "not_completed"
        metrics.browser_kept_open_for_owner = True
        metrics.add_failure(gate.reason)
        return OfflineFlowResult(
            outcome="stop",
            stage="stopped_review_documents",
            metrics=metrics,
            application_ready=False,
            submit_clicked=False,
            rotation_deletes=1,
            candidate_filename=decision.candidate.filename,
        )

    review_signals = PageSignals(
        url=review_page.url,
        looks_like_review_or_confirmation=True,
        looks_like_application_form=True,
    )
    assert classify_control("Submit application", page=review_signals) is (
        ControlClass.FINAL_SUBMIT
    )
    with pytest.raises(FinalSubmitGuardError):
        assert_may_activate("Submit application", page=review_signals)
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.submit_clicked_by_automation is False
    metrics.final_stage_reached = "review_or_confirmation"
    metrics.browser_kept_open_for_owner = handoff.browser_kept_open_for_owner
    metrics.submit_clicked = False
    metrics.application_submission = "not_completed"
    record_resume_snapshot(metrics, retry_snapshot, stage="handoff")
    metrics.add_note("APPLICATION READY FOR OWNER")

    posted = observe_submission_from_page_text(
        SUCCESS_BODY,
        url="https://www.seek.com.au/job/1/apply/success",
    )
    metrics.application_submission = posted.status
    metrics.submission_observation_evidence = posted.evidence
    assert metrics.submit_clicked is False
    return OfflineFlowResult(
        outcome="owner_ready",
        stage="review_or_confirmation",
        metrics=metrics,
        application_ready=True,
        submit_clicked=False,
        rotation_deletes=1,
        candidate_filename=decision.candidate.filename,
    )


def test_offline_whole_flow_blocked_upload_through_owner_success(
    tmp_path: Path,
) -> None:
    result = run_offline_aas_flow()
    metrics = result.metrics
    assert result.outcome == "owner_ready"
    assert result.application_ready is True
    assert result.submit_clicked is False
    assert result.rotation_deletes == 1
    assert result.candidate_filename == ATTR_CV
    assert result.candidate_filename != G360_CL
    assert metrics.resume_rotation_reason == "retry_expected_cv_selected"
    assert metrics.expected_cv_selected is True
    assert metrics.selected_resume_after_upload == G360_CV
    assert metrics.review_document_reason == "review_documents_match"
    assert metrics.review_observed_cv == G360_CV
    assert metrics.review_observed_cover_letter == G360_CL
    assert metrics.application_submission == "likely_submitted"
    assert metrics.submission_observation_evidence == "apply_success_url"
    assert metrics.submit_clicked is False
    assert metrics.default_resume_before == PROTECTED_DEFAULT
    assert metrics.resume_default_after_deletion == PROTECTED_DEFAULT
    assert metrics.default_changed_unexpected is False
    assert metrics.resume_delete_verification_reason == "deletion_verified"
    assert metrics.resume_delete_verification_poll_count == 3
    assert metrics.resume_list_count_after_deletion == metrics.resume_list_count_before - 1
    payload = metrics.to_dict()
    lifecycle = payload["resume_lifecycle"]
    assert lifecycle["review_document_reason"] == "review_documents_match"
    assert lifecycle["resume_rotation_reason"] == "retry_expected_cv_selected"
    path = tmp_path / "metrics.json"
    metrics.write_json(path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["submit_clicked"] is False
    assert loaded["application_submission"] == "likely_submitted"


def test_offline_flow_wrong_cv_after_retry_stops_without_handoff() -> None:
    result = run_offline_aas_flow(
        retry_selected_filename=NOVIGI_CV,
        include_expected_cv_on_retry=False,
    )
    assert result.outcome == "stop"
    assert result.application_ready is False
    assert result.submit_clicked is False
    assert result.stage == "stopped_cv_selection"
    assert result.metrics.resume_rotation_reason == "retry_failed_no_second_deletion"
    assert result.metrics.final_stage_reached == "stopped_cv_selection"
    assert result.metrics.submit_clicked is False
    assert result.rotation_deletes == 1


def test_offline_flow_default_change_during_rotation_stops_without_retry() -> None:
    result = run_offline_aas_flow(move_default_after_delete=True)
    assert result.outcome == "stop"
    assert result.application_ready is False
    assert result.submit_clicked is False
    assert result.metrics.resume_rotation_retry_attempted is False
    assert result.metrics.default_changed_unexpected is True
    assert result.metrics.resume_rotation_reason == "default_changed_after_deletion"


def test_offline_flow_delete_verification_timeout_does_not_retry() -> None:
    result = run_offline_aas_flow(
        delete_settles_after_polls=100,
        verification_timeout_ms=800,
        verification_poll_ms=400,
    )
    assert result.outcome == "stop"
    assert result.submit_clicked is False
    assert result.metrics.resume_rotation_reason == "resume_delete_verification_timeout"
    assert result.metrics.resume_rotation_retry_attempted is False
    assert result.rotation_deletes == 0
    assert result.metrics.resume_delete_verification_poll_count >= 1


def test_offline_flow_wrong_row_disappears_during_polling_stops() -> None:
    result = run_offline_aas_flow(
        delete_wrong_row=True,
        delete_settles_after_polls=1,
    )
    assert result.outcome == "stop"
    assert result.submit_clicked is False
    assert result.metrics.resume_rotation_reason == "wrong_row_disappeared"
    assert result.metrics.resume_rotation_retry_attempted is False


def test_offline_flow_verified_deletion_retries_once_only() -> None:
    result = run_offline_aas_flow()
    assert result.outcome == "owner_ready"
    assert result.metrics.resume_rotation_retry_attempted is True
    assert result.rotation_deletes == 1
    assert result.metrics.resume_rotation_reason == "retry_expected_cv_selected"


def test_offline_flow_review_wrong_cv_is_not_application_ready() -> None:
    result = run_offline_aas_flow(review_cv=NOVIGI_CV, review_cl=G360_CL)
    assert result.outcome == "stop"
    assert result.application_ready is False
    assert result.submit_clicked is False
    assert result.stage == "stopped_review_documents"
    assert result.metrics.review_document_reason == "review_cv_mismatch"
    assert result.metrics.final_stage_reached == "stopped_review_documents"
    assert result.metrics.application_submission == "not_completed"


def test_offline_flow_unknown_delete_confirmation_stops_without_guess() -> None:
    result = run_offline_aas_flow(confirmation_after_click=True)
    assert result.outcome == "stop"
    assert result.application_ready is False
    assert result.submit_clicked is False
    assert result.rotation_deletes == 0
    assert result.metrics.resume_rotation_reason == (
        "resume_delete_confirmation_unobserved"
    )
    assert result.metrics.resume_rotation_retry_attempted is False


def test_offline_flow_early_stop_metrics_serialise(tmp_path: Path) -> None:
    result = run_offline_aas_flow(early_stop_before_rotation=True)
    metrics = result.metrics
    payload = metrics.to_dict()
    assert "review_document_reason" in payload["resume_lifecycle"]
    path = tmp_path / "early-metrics.json"
    metrics.write_json(path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["resume_lifecycle"]["review_document_reason"] == ""
    assert loaded["submit_clicked"] is False
    assert loaded["final_stage_reached"] == "stopped_cv_selection"


def _hatch_selected_rows() -> list[tuple[str, bool]]:
    return [
        (f"{HATCH_CV}\nAdded 21 minutes ago\nMake this my default résumé", True),
        (f"{PROTECTED_DEFAULT}\nDefault", False),
        (NOVIGI_CV, False),
    ]


def run_offline_hatch_documents_advance_flow() -> OfflineFlowResult:
    """Proven Hatch 20260819T114421Z sequence: documents succeed, later pages must not re-verify."""
    metrics = SpikeMetrics(opportunity_id=HATCH_OPP)
    metrics.expected_cv_filename = HATCH_CV
    metrics.expected_cover_letter_filename = HATCH_CL
    rows = _hatch_selected_rows()
    snapshot = build_seek_resume_snapshot(rows)
    record_resume_snapshot(metrics, snapshot, stage="before")
    record_resume_snapshot(metrics, snapshot, stage="after_upload")
    assert snapshot.selected_filename == HATCH_CV
    assert snapshot.default_filename == PROTECTED_DEFAULT

    wait = evaluate_cv_upload_wait_tick(
        snapshot=snapshot,
        expected_filename=HATCH_CV,
        spinner_active=False,
        elapsed_ms=0,
    )
    assert wait.action == "success"
    metrics.cv_selection_reason = wait.reason
    metrics.expected_cv_selected = True
    metrics.selected_resume_after_upload = snapshot.selected_filename
    metrics.default_checkbox_reason = "checkbox_already_unchecked"

    documents_page = FakeSeekPage(
        body=HATCH_DOCUMENTS_BODY,
        cover_letter_radio_present=True,
        cover_letter_radio_checked=True,
        resume_file_count=1,
        default_checkbox=True,
    )
    assert choose_documents_visible(documents_page) is True
    documents_step_ready_to_continue(
        documents_page,
        expected_cv_filename=HATCH_CV,
        snapshot=snapshot,
        spinner_active=False,
    )
    documents_stage_complete = False
    documents_verified = metrics.cv_selection_reason == "expected_cv_selected"
    before = fingerprint_from_text(
        url="https://www.seek.com.au/job/94075152/apply",
        body_text=HATCH_DOCUMENTS_BODY,
    )
    after = fingerprint_from_text(
        url="https://www.seek.com.au/job/94075152/apply/questions",
        body_text=HATCH_QUESTIONS_BODY,
    )
    assert before.step_label == "choose documents"
    assert after.step_label == "answer employer questions"
    assert state_advanced(before, after)
    continue_outcome = "advanced"
    if documents_verified and continue_outcome == "advanced":
        documents_stage_complete = True

    questions = FakeSeekPage(
        body=HATCH_QUESTIONS_BODY,
        url="https://www.seek.com.au/job/94075152/apply/questions",
        cover_letter_radio_present=False,
        resume_file_count=0,
        cover_file_count=0,
        default_checkbox=False,
    )
    assert choose_documents_visible(questions) is False
    assert should_run_documents_stage(
        ui_visible=False,
        stage_complete=documents_stage_complete,
    ) is False
    empty = build_seek_resume_snapshot(())
    assert empty.selected_filename is None
    assert empty.entries == ()
    later_wait = evaluate_cv_upload_wait_tick(
        snapshot=empty,
        expected_filename=HATCH_CV,
        spinner_active=False,
        elapsed_ms=15_000,
    )
    run_later_verification = should_run_documents_stage(
        ui_visible=choose_documents_visible(questions),
        stage_complete=documents_stage_complete,
    )
    assert run_later_verification is False
    if run_later_verification:
        metrics.cv_selection_reason = later_wait.reason
        metrics.expected_cv_selected = False
        rotation = evaluate_rotation_decision(
            entries=empty.entries,
            upload_failure_reason=later_wait.reason,
            rotation_already_attempted=False,
        )
        metrics.resume_rotation_reason = rotation.reason
        metrics.resume_rotation_attempted = True
    assert metrics.cv_selection_reason == "expected_cv_selected"
    assert metrics.expected_cv_selected is True
    assert metrics.selected_resume_after_upload == HATCH_CV
    assert metrics.resume_rotation_attempted is False
    assert later_wait.reason == "expected_cv_not_present"

    profile = FakeSeekPage(
        body=HATCH_PROFILE_BODY,
        cover_letter_radio_present=False,
        resume_file_count=0,
        default_checkbox=False,
    )
    assert choose_documents_visible(profile) is False
    assert should_run_documents_stage(
        ui_visible=choose_documents_visible(profile),
        stage_complete=documents_stage_complete,
    ) is False

    review_body = REVIEW_TEMPLATE.format(cv=HATCH_CV, cl=HATCH_CL)
    assert is_final_review_page(review_body) is True
    observation = parse_review_document_filenames(review_body)
    gate = evaluate_review_document_gate(
        expected_cv=HATCH_CV,
        expected_cover_letter=HATCH_CL,
        observation=observation,
    )
    metrics.record_review_document_gate(
        observed_cv=gate.observed_cv,
        observed_cover_letter=gate.observed_cover_letter,
        reason=gate.reason,
    )
    assert gate.should_stop is False
    assert gate.allow_owner_handoff is True
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.submit_clicked_by_automation is False
    metrics.final_stage_reached = "review_or_confirmation"
    metrics.browser_kept_open_for_owner = True
    metrics.submit_clicked = False
    metrics.add_note("APPLICATION READY FOR OWNER")

    posted = apply_owner_session_submission_observation(
        metrics,
        body_text=HATCH_SUCCESS_BODY,
        url="https://www.seek.com.au/job/94075152/apply/success",
    )
    assert posted.status == "likely_submitted"
    assert metrics.submit_clicked is False
    return OfflineFlowResult(
        outcome="owner_ready",
        stage="review_or_confirmation",
        metrics=metrics,
        application_ready=True,
        submit_clicked=False,
        rotation_deletes=0,
    )


def test_offline_hatch_advance_does_not_reenter_documents_or_rotate() -> None:
    result = run_offline_hatch_documents_advance_flow()
    metrics = result.metrics
    assert result.outcome == "owner_ready"
    assert result.application_ready is True
    assert result.submit_clicked is False
    assert result.rotation_deletes == 0
    assert metrics.expected_cv_selected is True
    assert metrics.selected_resume_after_upload == HATCH_CV
    assert metrics.cv_selection_reason == "expected_cv_selected"
    assert metrics.resume_rotation_attempted is False
    assert metrics.resume_rotation_reason == ""
    assert metrics.review_document_reason == "review_documents_match"
    assert metrics.review_observed_cv == HATCH_CV
    assert metrics.review_observed_cover_letter == HATCH_CL
    assert metrics.application_submission == "likely_submitted"
    assert metrics.submit_clicked is False
    assert infer_step_label(HATCH_QUESTIONS_BODY) == "answer employer questions"
    assert infer_step_label(HATCH_DOCUMENTS_BODY) == "choose documents"


def test_choose_documents_stepper_text_alone_is_not_visible() -> None:
    page = FakeSeekPage(
        body="Choose documents\nAnswer employer questions\nContinue",
        cover_letter_radio_present=False,
        resume_file_count=0,
        default_checkbox=False,
    )
    assert choose_documents_visible(page) is False


def test_choose_documents_real_resume_controls_are_visible() -> None:
    page = FakeSeekPage(
        body="Choose documents",
        cover_letter_radio_present=False,
        resume_file_count=1,
        default_checkbox=False,
    )
    assert choose_documents_visible(page) is True


def test_genuine_choose_documents_missing_cv_still_triggers_rotation() -> None:
    rows = [
        (f"{PROTECTED_DEFAULT}\nDefault", False),
        (f"{NOVIGI_CV}", True),
    ]
    snapshot = build_seek_resume_snapshot(rows)
    page = FakeSeekPage(
        body=HATCH_DOCUMENTS_BODY.replace(HATCH_CV, NOVIGI_CV),
        cover_letter_radio_present=True,
        resume_file_count=1,
        default_checkbox=True,
    )
    assert choose_documents_visible(page) is True
    assert should_run_documents_stage(ui_visible=True, stage_complete=False) is True
    wait = evaluate_cv_upload_wait_tick(
        snapshot=snapshot,
        expected_filename=HATCH_CV,
        spinner_active=False,
        elapsed_ms=15_000,
    )
    assert wait.reason == "expected_cv_not_present"
    assert wait.observed_selected == NOVIGI_CV
    decision = evaluate_rotation_decision(
        entries=snapshot.entries,
        upload_failure_reason=wait.reason,
        rotation_already_attempted=False,
        default_observable_before=snapshot.default_observable,
    )
    assert decision.action == "attempt_delete"
