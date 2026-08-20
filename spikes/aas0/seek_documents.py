"""SEEK Choose Documents helpers for AAS-0 (spike-only)."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Mapping

from .answer_policy import is_default_resume_checkbox_label
from .default_checkbox_observation import (
    CHOSEN_VIA_LOCATOR_FIRST,
    LOCATOR_EXACT_NAME,
    LOCATOR_REGEX_FALLBACK,
    STAGE_AFTER_EXPECTED_CV_APPEARS,
    STAGE_AFTER_UNCHECK_RETURN_OR_THROW,
    STAGE_BEFORE_UNCHECK,
    STAGE_CHECKBOX_GUARD_DECISION,
    STAGE_CHECKBOX_SETTLE_POLL,
    append_default_checkbox_diagnostic,
    build_default_checkbox_observation_snapshot,
    diagnostic_has_stage,
)
from .document_gates import (
    CV_SELECTION_TIMEOUT_MS,
    CvUploadWaitDecision,
    DocumentsStepGateError,
    ReviewDocumentObservation,
    evaluate_cv_upload_wait_tick,
    evaluate_expected_cv_selection,
    filenames_equal,
    looks_like_resume_upload_busy,
    parse_review_document_filenames,
    snapshot_has_filename,
)
from .metrics import SpikeMetrics
from .upload_observation import (
    CHOSEN_VIA_EXISTING_SAVED_RESUME,
    CHOSEN_VIA_RESUME_FILE_ASSOCIATED_UPLOAD,
    STAGE_FIRST_CV_WAIT_FINAL,
    STAGE_FIRST_CV_WAIT_INITIAL,
    STAGE_FIRST_UPLOAD_AFTER,
    STAGE_FIRST_UPLOAD_BEFORE,
    STAGE_RETRY_CV_WAIT_FINAL,
    STAGE_RETRY_CV_WAIT_INITIAL,
    STAGE_RETRY_UPLOAD_AFTER,
    STAGE_RETRY_UPLOAD_BEFORE,
    UPLOAD_INTERACTION_CAPACITY,
    UPLOAD_INTERACTION_EXISTING_REUSED,
    UPLOAD_INTERACTION_FILECHOOSER,
    append_upload_diagnostic,
    build_upload_observation_snapshot,
    normalise_upload_accessible_name,
)
from .resume_lifecycle import (
    CHECKBOX_SETTLE_POLL_MS,
    CHECKBOX_SETTLE_TIMEOUT_MS,
    DefaultCheckboxOutcome,
    SeekResumeSnapshot,
    build_seek_resume_snapshot,
    checkbox_outcome_from_settle,
    classify_checkbox_settle_tick,
    detect_resume_capacity_message,
    evaluate_default_checkbox_guard,
    application_cv_is_structural_default,
    committed_structural_default_checkbox_locked,
    locked_structural_default_checkbox_outcome,
    extract_pdf_filename,
    row_is_structurally_default,
    select_cleanup_candidate,
    select_resume_row_text,
    should_skip_resume_radio_row,
)
from .resume_rotation import (
    SEEK_RESUME_DELETE_ACTION,
    SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
    SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
    DeleteConfirmationObservation,
    ResumeRowMenu,
    append_confirmation_diagnostic,
    build_delete_confirmation_observation,
    confirmation_accessible_name,
    empty_delete_confirmation_observation,
    normalise_confirmation_action_name,
    observation_diagnostic_snapshot,
    perform_one_resume_deletion,
    plan_resume_delete_confirmation,
    refuse_unobserved_resume_deletion,
)
from .state_progress import (
    CoverLetterGateError,
    assert_cover_letter_radio_checked,
    assert_may_continue_documents_step,
    detect_validation_messages,
    fingerprint_from_text,
)
from .upload_artefacts import (
    UnsafeUploadArtefactError,
    assert_safe_external_upload_pdf,
)

COVER_LETTER_UPLOAD_LABEL = "Upload a cover letter"
_DEFAULT_CHECKBOX_NAME = "Make this my default résumé"
FILECHOOSER_TIMEOUT_MS = 8_000
RESUME_UPLOAD_INTERACTION_FAILURES = frozenset(
    {
        "no_filechooser_event",
        "chooser_set_files_threw",
        "resume_upload_button_not_associated",
        "no_saved_resume_selected_for_upload",
    }
)

_FIND_RESUME_UPLOAD_BUTTON_JS = """() => {
  const resume = document.querySelector('#resume-fileFile');
  if (!resume) return null;
  const isUpload = (el) => {
    const raw = ((el.getAttribute('aria-label') || '') + ' '
      + (el.innerText || '')).replace(/\\u2060/g, ' ').replace(/\\s+/g, ' ').trim();
    return /^upload$/i.test(raw);
  };
  const coverInputs = [...document.querySelectorAll(
    'input[type=file][id*="cover" i], input[type=file][name*="cover" i], '
    + 'input[type=file][data-automation*="cover" i], input[type=file][id*="Cover"]'
  )].filter((el) => el !== resume);
  const label = resume.id
    ? document.querySelector('label[for="' + resume.id + '"]')
    : null;
  if (label) {
    const fromLabel = [label, ...label.querySelectorAll('button, [role="button"]')]
      .filter(isUpload);
    if (fromLabel.length === 1) return fromLabel[0];
  }
  let node = resume.parentElement;
  for (let depth = 1; depth <= 14 && node; depth += 1) {
    const uploads = [...node.querySelectorAll('button, [role="button"]')].filter(isUpload);
    const hasCover = coverInputs.some((el) => node.contains(el));
    if (uploads.length === 1 && !hasCover) return uploads[0];
    node = node.parentElement;
  }
  return null;
}"""

_DESCRIBE_ASSOCIATION_JS = """(button) => {
  const resume = document.querySelector('#resume-fileFile');
  const label = resume && resume.id
    ? document.querySelector('label[for="' + resume.id + '"]')
    : null;
  let depth = 0;
  let shared = resume;
  while (shared && button && !shared.contains(button)) {
    shared = shared.parentElement;
    depth += 1;
  }
  return {
    method: label && label.contains(button)
      ? 'label_for_resume-fileFile'
      : 'nearest_ancestor_excluding_cover_input',
    input_id: resume ? String(resume.id || '') : '',
    label_for: label ? String(label.getAttribute('for') || '') : '',
    ancestor_depth: depth,
    found: true,
  };
}"""


class ResumeUploadInteractionError(Exception):
    """Fail-closed résumé Upload / filechooser interaction. Do not fall back."""

    def __init__(self, reason: str, message: str = "") -> None:
        self.reason = reason
        super().__init__(message or reason)

_ROW_OVERFLOW_INFO_JS = """(el) => {
  let last = null;
  let node = el;
  for (let i = 0; i < 12 && node; i++) {
    const text = (node.innerText || '').trim();
    const count = (text.match(/\\.pdf\\b/gi) || []).length;
    if (count === 1) last = node;
    if (count > 1) break;
    node = node.parentElement;
  }
  if (!last) return {count: 0, expanded: false};
  const buttons = [...last.querySelectorAll('button, [role="button"]')];
  const openers = buttons.filter((b) => {
    const name = ((b.getAttribute('aria-label') || '') + ' '
      + (b.textContent || '')).replace(/\\s+/g, ' ').trim();
    if (/^(delete|download)$/i.test(name)) return false;
    const hp = (b.getAttribute('aria-haspopup') || '').toLowerCase();
    if (hp === 'true' || hp === 'menu' || hp === 'listbox') return true;
    if (b.hasAttribute('aria-expanded')) return true;
    if (/^(more|more options|options|actions|open menu|menu)$/i.test(name)) {
      return true;
    }
    return false;
  });
  const expanded = openers.some(
    (b) => (b.getAttribute('aria-expanded') || '').toLowerCase() === 'true'
  );
  return {count: openers.length, expanded};
}"""

_CLICK_ROW_OVERFLOW_JS = """(el) => {
  let last = null;
  let node = el;
  for (let i = 0; i < 12 && node; i++) {
    const text = (node.innerText || '').trim();
    const count = (text.match(/\\.pdf\\b/gi) || []).length;
    if (count === 1) last = node;
    if (count > 1) break;
    node = node.parentElement;
  }
  if (!last) return 'overflow_not_found_on_row';
  const buttons = [...last.querySelectorAll('button, [role="button"]')];
  const openers = buttons.filter((b) => {
    const name = ((b.getAttribute('aria-label') || '') + ' '
      + (b.textContent || '')).replace(/\\s+/g, ' ').trim();
    if (/^(delete|download)$/i.test(name)) return false;
    const hp = (b.getAttribute('aria-haspopup') || '').toLowerCase();
    if (hp === 'true' || hp === 'menu' || hp === 'listbox') return true;
    if (b.hasAttribute('aria-expanded')) return true;
    if (/^(more|more options|options|actions|open menu|menu)$/i.test(name)) {
      return true;
    }
    return false;
  });
  if (openers.length < 1) return 'overflow_not_found_on_row';
  if (openers.length !== 1) return 'overflow_ambiguous_on_row';
  openers[0].click();
  return 'opened';
}"""


def page_body_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:  # noqa: BLE001
        return ""


def capture_fingerprint(page, *, marker: str = ""):
    return fingerprint_from_text(
        url=getattr(page, "url", "") or "",
        body_text=page_body_text(page),
        marker=marker,
    )


def _locator_count(locator) -> int:
    try:
        return int(locator.count())
    except Exception:  # noqa: BLE001
        return 0


def documents_step_controls_present(page) -> bool:
    """True when real Choose Documents controls exist (not stepper text)."""
    if _locator_count(resume_file_input(page)) > 0:
        return True
    if _locator_count(cover_letter_file_input(page)) > 0:
        return True
    if cover_letter_method_radios_present(page):
        return True
    if _locator_count(default_resume_checkbox(page)) > 0:
        return True
    return False


def choose_documents_visible(page) -> bool:
    """Active Choose Documents UI only. Stepper text is not sufficient."""
    return documents_step_controls_present(page)


def should_run_documents_stage(*, ui_visible: bool, stage_complete: bool) -> bool:
    """Upload / confirm / rotation only while documents UI is active and incomplete."""
    return bool(ui_visible) and not bool(stage_complete)


def cover_letter_method_radios_present(page) -> bool:
    radio = page.get_by_role("radio", name=COVER_LETTER_UPLOAD_LABEL)
    try:
        return radio.count() > 0
    except Exception:  # noqa: BLE001
        return False


def is_cover_letter_upload_radio_checked(page) -> bool:
    radio = page.get_by_role("radio", name=COVER_LETTER_UPLOAD_LABEL)
    try:
        if radio.count() == 0:
            return False
        return bool(radio.first.is_checked())
    except Exception:  # noqa: BLE001
        return False


def select_cover_letter_upload_method(page, metrics: SpikeMetrics) -> bool:
    """Select and verify the Upload cover-letter radio. Returns True if checked."""
    radio = page.get_by_role("radio", name=COVER_LETTER_UPLOAD_LABEL)
    if radio.count() == 0:
        metrics.add_note("Cover-letter upload radio not present on page")
        return False
    try:
        radio.first.check(timeout=5_000)
    except Exception:
        try:
            radio.first.click(timeout=5_000)
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"cover_letter_radio_select_failed: {error}")
            return False
    page.wait_for_timeout(400)
    checked = is_cover_letter_upload_radio_checked(page)
    if checked:
        metrics.add_note("Cover-letter upload radio checked and verified")
    else:
        metrics.add_failure(
            "Cover-letter upload radio click did not result in checked state"
        )
    return checked


def cover_letter_file_input(page):
    return page.locator(
        'input[type=file][data-automation*="cover"], '
        'input[type=file][id*="cover"], '
        'input[type=file][name*="cover"], '
        'input[type=file][aria-label*="cover"], '
        'input[type=file][data-automation*="Cover"], '
        'input[type=file][id*="Cover"]'
    )


def resume_file_input(page):
    return page.locator(
        'input[type=file][data-automation*="resume"], '
        'input[type=file][id*="resume"], '
        'input[type=file][name*="resume"], '
        'input[type=file][aria-label*="resume"], '
        'input[type=file][data-automation*="Resume"]'
    )


_FILE_INPUT_DOM_JS = """el => ({
  tag_name: el.tagName ? String(el.tagName).toLowerCase() : '',
  input_type: String(el.type || el.getAttribute('type') || ''),
  attached: !!el.isConnected,
  id: String(el.id || ''),
  name: String(el.getAttribute('name') || ''),
  aria_label: String(el.getAttribute('aria-label') || ''),
  data_automation: String(el.getAttribute('data-automation') || ''),
})"""

_UPLOAD_CONTROL_DOM_JS = """el => {
  const svgs = [...el.querySelectorAll('svg')].slice(0, 4).map(
    (node) => String(node.getAttribute('class') || '').slice(0, 160)
  );
  return {
    tag_name: el.tagName ? String(el.tagName).toLowerCase() : '',
    role: String(el.getAttribute('role') || 'button'),
    aria_busy: el.getAttribute('aria-busy'),
    aria_label: String(el.getAttribute('aria-label') || ''),
    class_name: String(el.className || '').slice(0, 240),
    inner_text: String(el.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 80),
    svg_classes: svgs,
    progressbar_count: el.querySelectorAll('[role="progressbar"]').length,
    aria_busy_child_count: el.querySelectorAll('[aria-busy="true"]').length,
    spin_or_loading_count: el.querySelectorAll(
      'svg[class*="spin" i], [class*="loading" i]'
    ).length,
  };
}"""


def inspect_file_input_matches(locator) -> list[dict]:
    """Read-only per-match file-input dump. Never clicks or sets files."""
    matches: list[dict] = []
    try:
        count = locator.count()
    except Exception:  # noqa: BLE001
        return matches
    for index in range(min(int(count), 12)):
        item = locator.nth(index)
        record: dict = {"index": index}
        try:
            record["visible"] = bool(item.is_visible())
        except Exception:  # noqa: BLE001
            record["visible"] = None
        try:
            record["enabled"] = bool(item.is_enabled())
        except Exception:  # noqa: BLE001
            record["enabled"] = None
        try:
            dumped = item.evaluate(_FILE_INPUT_DOM_JS)
        except Exception:  # noqa: BLE001
            dumped = {}
        if isinstance(dumped, dict):
            record.update(dumped)
        try:
            box = item.bounding_box()
        except Exception:  # noqa: BLE001
            box = None
        record["bounding_box"] = box if isinstance(box, dict) else box
        matches.append(record)
    return matches


def inspect_resume_upload_controls(page) -> tuple[list[dict], bool, bool, bool]:
    """Read-only Upload-button dump plus the same detector inputs as spinner_active.

    Detection rules are not changed; this only persists evidence.
    """
    aria_busy = False
    has_progress = False
    uploading_text = False
    controls: list[dict] = []
    try:
        buttons = page.get_by_role("button", name=re.compile(r"^upload$", re.I))
        count = min(buttons.count(), 6)
        for index in range(count):
            button = buttons.nth(index)
            record: dict = {"index": index}
            try:
                record["visible"] = bool(button.is_visible())
            except Exception:  # noqa: BLE001
                record["visible"] = None
            try:
                record["enabled"] = bool(button.is_enabled())
            except Exception:  # noqa: BLE001
                record["enabled"] = None
            try:
                record["accessible_name"] = (button.inner_text() or "").strip() or "Upload"
            except Exception:  # noqa: BLE001
                record["accessible_name"] = "Upload"
            try:
                dumped = button.evaluate(_UPLOAD_CONTROL_DOM_JS)
            except Exception:  # noqa: BLE001
                dumped = {}
            if isinstance(dumped, dict):
                record.update(dumped)
                if (dumped.get("aria_busy") or "").strip().lower() == "true":
                    aria_busy = True
                if int(dumped.get("progressbar_count") or 0) > 0:
                    has_progress = True
                if int(dumped.get("aria_busy_child_count") or 0) > 0:
                    has_progress = True
                if int(dumped.get("spin_or_loading_count") or 0) > 0:
                    has_progress = True
            try:
                if (button.get_attribute("aria-busy") or "").strip().lower() == "true":
                    aria_busy = True
                    record["aria_busy"] = "true"
            except Exception:  # noqa: BLE001
                pass
            controls.append(record)
    except Exception:  # noqa: BLE001
        pass
    try:
        loc = page.get_by_text(re.compile(r"\buploading\b", re.I))
        uploading_text = loc.count() > 0 and loc.first.is_visible()
    except Exception:  # noqa: BLE001
        uploading_text = False
    return controls, aria_busy, has_progress, uploading_text


def capture_upload_observation(
    page,
    *,
    path: Path | str | None,
    stage: str,
    expected_cv_path: str | None = None,
    expected_cv_filename: str | None = None,
    retry_cv: bool | None = None,
    already_cv_skip: bool | None = None,
    resume_input_count_zero_skip: bool | None = None,
    upload_interaction: str | None = None,
    resume_upload_association: Mapping[str, Any] | None = None,
    filechooser_event_observed: bool | None = None,
    chooser_set_files_started: bool | None = None,
    chooser_set_files_returned: bool | None = None,
    chooser_set_files_threw: bool | None = None,
    chooser_set_files_exception_type: str | None = None,
    chooser_set_files_exception_message: str | None = None,
    upload_settle_elapsed_ms: int | None = None,
    default_before_upload: str | None = None,
    default_after_upload: str | None = None,
    default_after_uncheck_settle: str | None = None,
    chosen_via: str | None = None,
    set_input_files_started: bool | None = None,
    set_input_files_returned: bool | None = None,
    set_input_files_threw: bool | None = None,
    set_input_files_exception_type: str | None = None,
    set_input_files_exception_message: str | None = None,
    snapshot: SeekResumeSnapshot | None = None,
    cv_wait_action: str | None = None,
    cv_wait_reason: str | None = None,
    expected_cv_present_before_upload: bool | None = None,
    saved_resume_count: int | None = None,
    upload_attempted: bool | None = None,
    capacity_modal_observed: bool | None = None,
    existing_expected_cv_reused: bool | None = None,
) -> None:
    """Append one read-only upload stage. Swallow errors so decisions stay unchanged."""
    if path is None:
        return
    try:
        resume_matches = inspect_file_input_matches(resume_file_input(page))
        try:
            cover_count = cover_letter_file_input(page).count()
        except Exception:  # noqa: BLE001
            cover_count = None
        try:
            cl_radio = is_cover_letter_upload_radio_checked(page)
        except Exception:  # noqa: BLE001
            cl_radio = None
        controls, aria_busy, has_progress, uploading_text = inspect_resume_upload_controls(
            page
        )
        spinner = resume_upload_spinner_active(page)
        if snapshot is None:
            snapshot = observe_resume_snapshot(page)
        expected_present = None
        expected_selected = None
        if expected_cv_filename:
            expected_present = snapshot_has_filename(snapshot, expected_cv_filename)
            expected_selected = filenames_equal(
                expected_cv_filename, snapshot.selected_filename
            )
        match_count = len(resume_matches)
        chosen_index = 0 if match_count else None
        if default_after_upload is None:
            default_after_upload = snapshot.default_filename
        append_upload_diagnostic(
            path,
            build_upload_observation_snapshot(
                stage=stage,
                expected_cv_path=expected_cv_path,
                expected_cv_filename=expected_cv_filename,
                retry_cv=retry_cv,
                resume_input_matches=resume_matches,
                chosen_index=chosen_index,
                chosen_via=chosen_via,
                cover_letter_input_count=cover_count,
                cover_letter_radio_checked=cl_radio,
                already_cv_skip=already_cv_skip,
                resume_input_count_zero_skip=resume_input_count_zero_skip,
                upload_interaction=upload_interaction,
                resume_upload_association=resume_upload_association,
                filechooser_event_observed=filechooser_event_observed,
                chooser_set_files_started=chooser_set_files_started,
                chooser_set_files_returned=chooser_set_files_returned,
                chooser_set_files_threw=chooser_set_files_threw,
                chooser_set_files_exception_type=chooser_set_files_exception_type,
                chooser_set_files_exception_message=chooser_set_files_exception_message,
                upload_settle_elapsed_ms=upload_settle_elapsed_ms,
                default_before_upload=default_before_upload,
                default_after_upload=default_after_upload,
                default_after_uncheck_settle=default_after_uncheck_settle,
                set_input_files_started=set_input_files_started,
                set_input_files_returned=set_input_files_returned,
                set_input_files_threw=set_input_files_threw,
                set_input_files_exception_type=set_input_files_exception_type,
                set_input_files_exception_message=set_input_files_exception_message,
                spinner_detector=spinner,
                upload_button_aria_busy=aria_busy,
                upload_control_has_progress=has_progress,
                uploading_text_visible=uploading_text,
                upload_controls=controls,
                resume_filenames=[entry.filename for entry in snapshot.entries],
                selected_filename=snapshot.selected_filename,
                structural_default_filename=snapshot.default_filename,
                expected_cv_present=expected_present,
                expected_cv_selected=expected_selected,
                cv_wait_action=cv_wait_action,
                cv_wait_reason=cv_wait_reason,
                expected_cv_present_before_upload=expected_cv_present_before_upload,
                saved_resume_count=(
                    saved_resume_count
                    if saved_resume_count is not None
                    else len(snapshot.entries)
                ),
                upload_attempted=upload_attempted,
                capacity_modal_observed=capacity_modal_observed,
                existing_expected_cv_reused=existing_expected_cv_reused,
            ),
        )
    except Exception:  # noqa: BLE001
        return


def resolve_default_resume_checkbox(page) -> tuple[object, str]:
    """Same locator as ``default_resume_checkbox``, plus which name matcher won."""
    named = page.get_by_role("checkbox", name=_DEFAULT_CHECKBOX_NAME)
    try:
        if named.count() > 0:
            return named, LOCATOR_EXACT_NAME
    except Exception:  # noqa: BLE001
        pass
    return (
        page.get_by_role(
            "checkbox",
            name=re.compile(r"make this my default r", re.I),
        ),
        LOCATOR_REGEX_FALLBACK,
    )


def default_resume_checkbox(page):
    locator, _source = resolve_default_resume_checkbox(page)
    return locator


_CHECKBOX_DOM_JS = """el => {
  const parent = el.parentElement;
  const wrap = el.closest('label, [class], div') || parent;
  return {
    tag_name: el.tagName ? String(el.tagName).toLowerCase() : '',
    input_type: String(el.type || el.getAttribute('type') || ''),
    role: String(el.getAttribute('role') || ''),
    aria_label: String(el.getAttribute('aria-label') || ''),
    aria_checked: el.getAttribute('aria-checked'),
    checked_attribute: el.getAttribute('checked'),
    checked_property: (typeof el.checked === 'boolean') ? el.checked : null,
    wrapper_tag: wrap && wrap.tagName ? String(wrap.tagName).toLowerCase() : '',
    wrapper_class: wrap ? String(wrap.className || '').slice(0, 240) : '',
    wrapper_role: wrap ? String(wrap.getAttribute('role') || '') : '',
    wrapper_data_automation: wrap
      ? String(wrap.getAttribute('data-automation') || '')
      : '',
  };
}"""

_CHECKBOX_ACCESSIBLE_NAME_JS = """el => {
  const labelled = el.getAttribute('aria-labelledby');
  if (labelled) {
    const node = document.getElementById(labelled);
    if (node) return (node.innerText || '').replace(/\\s+/g, ' ').trim();
  }
  const id = el.id;
  if (id) {
    const lab = document.querySelector('label[for="' + CSS.escape(id) + '"]');
    if (lab) return (lab.innerText || '').replace(/\\s+/g, ' ').trim();
  }
  const wrap = el.closest('label');
  if (wrap) return (wrap.innerText || '').replace(/\\s+/g, ' ').trim();
  return (el.innerText || '').replace(/\\s+/g, ' ').trim();
}"""


def inspect_default_checkbox_matches(locator) -> list[dict]:
    """Read-only per-match DOM/accessibility dump. Never clicks."""
    matches: list[dict] = []
    try:
        count = locator.count()
    except Exception:  # noqa: BLE001
        return matches
    for index in range(min(int(count), 12)):
        item = locator.nth(index)
        record: dict = {"index": index}
        try:
            record["visible"] = bool(item.is_visible())
        except Exception:  # noqa: BLE001
            record["visible"] = None
        try:
            record["enabled"] = bool(item.is_enabled())
        except Exception:  # noqa: BLE001
            record["enabled"] = None
        try:
            record["is_checked"] = bool(item.is_checked())
        except Exception:  # noqa: BLE001
            record["is_checked"] = None
        try:
            dumped = item.evaluate(_CHECKBOX_DOM_JS)
        except Exception:  # noqa: BLE001
            dumped = {}
        if isinstance(dumped, dict):
            record.update(dumped)
        else:
            dumped = {}
        try:
            if not record.get("aria_label"):
                record["aria_label"] = item.get_attribute("aria-label")
        except Exception:  # noqa: BLE001
            pass
        try:
            name = item.evaluate(_CHECKBOX_ACCESSIBLE_NAME_JS)
        except Exception:  # noqa: BLE001
            name = record.get("aria_label") or ""
        record["accessible_name"] = name if isinstance(name, str) else ""
        if record.get("aria_checked") is None:
            try:
                record["aria_checked"] = item.get_attribute("aria-checked")
            except Exception:  # noqa: BLE001
                record["aria_checked"] = None
        if record.get("checked_attribute") is None:
            try:
                record["checked_attribute"] = item.get_attribute("checked")
            except Exception:  # noqa: BLE001
                record["checked_attribute"] = None
        matches.append(record)
    return matches


def capture_default_checkbox_observation(
    page,
    *,
    path: Path | str | None,
    stage: str,
    expected_cv_filename: str | None = None,
    snapshot: SeekResumeSnapshot | None = None,
    was_checked: bool | None = None,
    uncheck_attempted: bool | None = None,
    uncheck_returned: bool | None = None,
    uncheck_threw: bool | None = None,
    uncheck_exception_type: str | None = None,
    uncheck_exception_message: str | None = None,
    checked_immediately_after_uncheck: bool | None = None,
    checked_after_400ms_wait: bool | None = None,
    checkbox_enabled: bool | None = None,
    baseline_default_filename: str | None = None,
    settle_poll_index: int | None = None,
    settle_poll_count: int | None = None,
    settle_wait_ms: int | None = None,
    guard: DefaultCheckboxOutcome | None = None,
) -> None:
    """Append one read-only stage dump. Swallow errors so decisions stay unchanged."""
    if path is None:
        return
    try:
        locator, source = resolve_default_resume_checkbox(page)
        matches = inspect_default_checkbox_matches(locator)
        match_count = len(matches)
        chosen_index = 0 if match_count else None
        chosen_via = CHOSEN_VIA_LOCATOR_FIRST if chosen_index is not None else None
        if snapshot is None:
            snapshot = observe_resume_snapshot(page)
        expected_present = None
        if expected_cv_filename:
            expected_present = snapshot_has_filename(snapshot, expected_cv_filename)
        append_default_checkbox_diagnostic(
            path,
            build_default_checkbox_observation_snapshot(
                stage=stage,
                locator_source=source,
                matches=matches,
                chosen_index=chosen_index,
                chosen_via=chosen_via,
                structural_default_filename=snapshot.default_filename,
                selected_filename=snapshot.selected_filename,
                expected_cv_filename=expected_cv_filename,
                expected_cv_present=expected_present,
                was_checked=was_checked,
                uncheck_attempted=uncheck_attempted,
                uncheck_returned=uncheck_returned,
                uncheck_threw=uncheck_threw,
                uncheck_exception_type=uncheck_exception_type,
                uncheck_exception_message=uncheck_exception_message,
                checked_immediately_after_uncheck=checked_immediately_after_uncheck,
                checked_after_400ms_wait=checked_after_400ms_wait,
                checkbox_enabled=checkbox_enabled,
                baseline_default_filename=baseline_default_filename,
                settle_poll_index=settle_poll_index,
                settle_poll_count=settle_poll_count,
                settle_wait_ms=settle_wait_ms,
                guard_reason=None if guard is None else guard.reason,
                guard_should_stop=None if guard is None else guard.should_stop,
                guard_uncheck_succeeded=(
                    None if guard is None else guard.uncheck_succeeded
                ),
            ),
        )
    except Exception:  # noqa: BLE001
        return


def dump_expected_cv_appeared_once(
    page,
    *,
    path: Path | str | None,
    expected_cv_filename: str | None,
    dumped_flag: list[bool] | None,
    snapshot: SeekResumeSnapshot | None = None,
) -> None:
    """Dump ``after_expected_cv_appears`` once, when the expected CV is already present.

    Does not wait. If the CV is not yet in the snapshot, this is a no-op.
    """
    if path is None or not expected_cv_filename:
        return
    if dumped_flag is not None and dumped_flag and dumped_flag[0]:
        return
    if dumped_flag is None and diagnostic_has_stage(
        path, STAGE_AFTER_EXPECTED_CV_APPEARS
    ):
        return
    try:
        current = snapshot if snapshot is not None else observe_resume_snapshot(page)
        if not snapshot_has_filename(current, expected_cv_filename):
            return
        capture_default_checkbox_observation(
            page,
            path=path,
            stage=STAGE_AFTER_EXPECTED_CV_APPEARS,
            expected_cv_filename=expected_cv_filename,
            snapshot=current,
        )
        if dumped_flag is not None:
            if dumped_flag:
                dumped_flag[0] = True
            else:
                dumped_flag.append(True)
    except Exception:  # noqa: BLE001
        return


def cover_letter_filename_visible(page, filename: str) -> bool:
    stem = Path(filename).name
    try:
        loc = page.get_by_text(stem, exact=False)
        return loc.count() > 0 and loc.first.is_visible()
    except Exception:  # noqa: BLE001
        return False


def _radio_row_text(radio) -> str:
    """Résumé row innerText, including the Default badge when it lives on the row.

    Walks ancestors inner-to-outer and keeps the outermost node that still
    mentions exactly one PDF (see ``select_resume_row_text``).
    """
    try:
        texts = radio.evaluate(
            """el => {
              const texts = [];
              let node = el;
              for (let i = 0; i < 12 && node; i++) {
                texts.push((node.innerText || '').trim());
                node = node.parentElement;
              }
              return texts;
            }"""
        )
        if isinstance(texts, list):
            return select_resume_row_text([str(item or "") for item in texts])
        return str(texts or "")
    except Exception:  # noqa: BLE001
        return ""


def observe_resume_snapshot(page) -> SeekResumeSnapshot:
    """Parse visible résumé radios. Fail closed to not-observable on probe errors."""
    rows: list[tuple[str, bool]] = []
    try:
        radios = page.get_by_role("radio")
        count = radios.count()
    except Exception:  # noqa: BLE001
        return build_seek_resume_snapshot(())
    for index in range(count):
        radio = radios.nth(index)
        try:
            if not radio.is_visible():
                continue
            text = _radio_row_text(radio)
            selected = bool(radio.is_checked())
        except Exception:  # noqa: BLE001
            continue
        rows.append((text, selected))
    return build_seek_resume_snapshot(rows)


def resume_upload_spinner_active(page) -> bool:
    """True when the Choose-documents résumé Upload control still looks busy."""
    aria_busy = False
    has_progress = False
    uploading_text = False
    try:
        buttons = page.get_by_role("button", name=re.compile(r"^upload$", re.I))
        count = min(buttons.count(), 6)
        for index in range(count):
            button = buttons.nth(index)
            try:
                if not button.is_visible():
                    continue
                if (button.get_attribute("aria-busy") or "").strip().lower() == "true":
                    aria_busy = True
                if (
                    button.locator(
                        '[role="progressbar"], [aria-busy="true"], '
                        'svg[class*="spin" i], [class*="loading" i]'
                    ).count()
                    > 0
                ):
                    has_progress = True
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    try:
        loc = page.get_by_text(re.compile(r"\buploading\b", re.I))
        uploading_text = loc.count() > 0 and loc.first.is_visible()
    except Exception:  # noqa: BLE001
        uploading_text = False
    return looks_like_resume_upload_busy(
        upload_button_aria_busy=aria_busy,
        upload_control_has_progress=has_progress,
        uploading_text_visible=uploading_text,
    )


def click_resume_radio_by_filename(page, expected_filename: str) -> bool:
    """Check the résumé radio whose row filename equals the expected export CV."""
    expected = (expected_filename or "").strip()
    if not expected:
        return False
    try:
        radios = page.get_by_role("radio")
        count = radios.count()
    except Exception:  # noqa: BLE001
        return False
    for index in range(count):
        radio = radios.nth(index)
        try:
            if not radio.is_visible():
                continue
            filename = extract_pdf_filename(_radio_row_text(radio))
            if not filenames_equal(expected, filename):
                continue
            try:
                radio.check(timeout=5_000)
            except Exception:  # noqa: BLE001
                radio.click(timeout=5_000)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def confirm_expected_cv_for_application(
    page,
    *,
    expected_cv_filename: str,
    metrics: SpikeMetrics,
    timeout_ms: int = CV_SELECTION_TIMEOUT_MS,
    poll_ms: int = 400,
    diagnostic_path: Path | str | None = None,
    diagnostic_cv_appeared: list[bool] | None = None,
    upload_diagnostic_path: Path | str | None = None,
    upload_wait_phase: str | None = None,
) -> CvUploadWaitDecision:
    """Wait until the expected CV row is selected, or fail closed."""
    metrics.expected_cv_filename = expected_cv_filename
    started = time.monotonic()
    last = CvUploadWaitDecision(
        action="stop",
        reason="expected_cv_not_present",
        present=False,
        selected=False,
        observed_selected=None,
        spinner_active=False,
    )
    dumped_wait_initial = False
    while True:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        spinner = resume_upload_spinner_active(page)
        snapshot = observe_resume_snapshot(page)
        last = evaluate_cv_upload_wait_tick(
            snapshot=snapshot,
            expected_filename=expected_cv_filename,
            spinner_active=spinner,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
        )
        if last.present:
            dump_expected_cv_appeared_once(
                page,
                path=diagnostic_path,
                expected_cv_filename=expected_cv_filename,
                dumped_flag=diagnostic_cv_appeared,
                snapshot=snapshot,
            )
        wait_stage_initial = None
        wait_stage_final = None
        if upload_wait_phase == "first":
            wait_stage_initial = STAGE_FIRST_CV_WAIT_INITIAL
            wait_stage_final = STAGE_FIRST_CV_WAIT_FINAL
        elif upload_wait_phase == "retry":
            wait_stage_initial = STAGE_RETRY_CV_WAIT_INITIAL
            wait_stage_final = STAGE_RETRY_CV_WAIT_FINAL
        if wait_stage_initial and not dumped_wait_initial:
            capture_upload_observation(
                page,
                path=upload_diagnostic_path,
                stage=wait_stage_initial,
                expected_cv_filename=expected_cv_filename,
                retry_cv=upload_wait_phase == "retry",
                snapshot=snapshot,
                cv_wait_action=last.action,
                cv_wait_reason=last.reason,
                upload_settle_elapsed_ms=elapsed_ms,
                default_after_upload=snapshot.default_filename,
            )
            dumped_wait_initial = True
        if last.action == "attempt_select":
            clicked = click_resume_radio_by_filename(page, expected_cv_filename)
            metrics.add_note(
                f"attempted_select_expected_cv clicked={clicked} "
                f"expected={expected_cv_filename!r} "
                f"observed_selected={last.observed_selected!r}"
            )
            page.wait_for_timeout(min(poll_ms, 400))
            continue
        if last.action == "keep_waiting":
            page.wait_for_timeout(poll_ms)
            continue
        if wait_stage_final:
            capture_upload_observation(
                page,
                path=upload_diagnostic_path,
                stage=wait_stage_final,
                expected_cv_filename=expected_cv_filename,
                retry_cv=upload_wait_phase == "retry",
                snapshot=snapshot,
                cv_wait_action=last.action,
                cv_wait_reason=last.reason,
                upload_settle_elapsed_ms=elapsed_ms,
                default_after_upload=snapshot.default_filename,
            )
        metrics.cv_selection_reason = last.reason
        metrics.upload_completion_reason = last.reason
        metrics.selected_resume_after_upload = last.observed_selected
        metrics.expected_cv_selected = last.action != "stop" and last.selected
        metrics.add_note(
            f"cv_selection action={last.action} reason={last.reason} "
            f"present={last.present} selected={last.selected} "
            f"observed={last.observed_selected!r} spinner={last.spinner_active}"
        )
        if last.action == "stop":
            metrics.add_failure(
                "Expected CV was not selected for this application: "
                f"expected={expected_cv_filename!r} "
                f"observed_selected={last.observed_selected!r} "
                f"reason={last.reason}"
            )
        return last


def observe_review_documents(page) -> ReviewDocumentObservation:
    return parse_review_document_filenames(page_body_text(page))


def uncheck_default_checkbox_if_checked(
    page,
    metrics: SpikeMetrics,
    *,
    diagnostic_path: Path | str | None = None,
    expected_cv_filename: str | None = None,
    baseline_default_filename: str | None = None,
    baseline_default_observable: bool = False,
    timeout_ms: int = CHECKBOX_SETTLE_TIMEOUT_MS,
    poll_ms: int = CHECKBOX_SETTLE_POLL_MS,
) -> DefaultCheckboxOutcome:
    """Uncheck 'Make this my default résumé' if SEEK auto-checked it.

    ``uncheck()`` throwing is diagnostic only. Success is the settled
    checkbox-unchecked + original structural Default restored state.
    Never auto-restores Default. A checked **and disabled** checkbox on the
    already-Default selected résumé is a committed Default: STOP immediately
    without ``uncheck()`` or settle polling. Checked **and enabled** remains
    the new-upload uncheck path.
    """

    def _dump(stage: str, **fields: object) -> None:
        capture_default_checkbox_observation(
            page,
            path=diagnostic_path,
            stage=stage,
            expected_cv_filename=expected_cv_filename,
            baseline_default_filename=baseline_default_filename,
            **fields,
        )

    def _record_outcome(outcome: DefaultCheckboxOutcome) -> DefaultCheckboxOutcome:
        metrics.default_checkbox_reason = outcome.reason
        metrics.default_checkbox_still_checked = outcome.still_checked
        metrics.default_checkbox_uncheck_threw = outcome.uncheck_threw
        metrics.default_checkbox_baseline = outcome.baseline_default_filename
        metrics.default_checkbox_settled_default = outcome.settled_default_filename
        metrics.default_checkbox_settle_poll_count = outcome.settle_poll_count
        metrics.default_checkbox_settle_wait_ms = outcome.settle_wait_ms
        if outcome.reason == "default_changed_unexpectedly":
            metrics.default_changed_unexpected = True
            metrics.default_change_reason = outcome.reason
        return outcome

    box = default_resume_checkbox(page)
    try:
        if box.count() == 0:
            outcome = evaluate_default_checkbox_guard(
                present=False,
                was_checked=False,
                still_checked=False,
                uncheck_attempted=False,
            )
            _dump(
                STAGE_BEFORE_UNCHECK,
                was_checked=False,
                uncheck_attempted=False,
            )
            _dump(
                STAGE_CHECKBOX_GUARD_DECISION,
                was_checked=False,
                uncheck_attempted=False,
                guard=outcome,
            )
            metrics.add_note(f"Default résumé checkbox: {outcome.reason}")
            return _record_outcome(outcome)
        target = box.first
        was_checked = bool(target.is_checked())
        enabled: bool | None
        try:
            enabled = bool(target.is_enabled())
        except Exception:  # noqa: BLE001
            enabled = None
        snapshot = observe_resume_snapshot(page)
        _dump(
            STAGE_BEFORE_UNCHECK,
            was_checked=was_checked,
            uncheck_attempted=False,
            checkbox_enabled=enabled,
            snapshot=snapshot,
        )
        if not was_checked:
            outcome = evaluate_default_checkbox_guard(
                present=True,
                was_checked=False,
                still_checked=False,
                uncheck_attempted=False,
            )
            _dump(
                STAGE_CHECKBOX_GUARD_DECISION,
                was_checked=False,
                uncheck_attempted=False,
                checkbox_enabled=enabled,
                snapshot=snapshot,
                guard=outcome,
            )
            metrics.add_note(f"Default résumé checkbox: {outcome.reason}")
            return _record_outcome(outcome)
        if committed_structural_default_checkbox_locked(
            checked=True,
            enabled=enabled,
            selected_filename=snapshot.selected_filename,
            default_filename=snapshot.default_filename,
        ):
            outcome = locked_structural_default_checkbox_outcome(
                default_filename=snapshot.default_filename,
                selected_filename=snapshot.selected_filename,
            )
            _dump(
                STAGE_CHECKBOX_GUARD_DECISION,
                was_checked=True,
                uncheck_attempted=False,
                checkbox_enabled=False,
                snapshot=snapshot,
                guard=outcome,
            )
            metrics.add_failure(
                "SEEK Default checkbox is checked and disabled on the "
                "committed structural Default. Not unchecking and not "
                "transferring Default. "
                f"reason={outcome.reason} selected={snapshot.selected_filename!r} "
                f"default={snapshot.default_filename!r}"
            )
            metrics.add_note(f"Default résumé checkbox: {outcome.reason}")
            return _record_outcome(outcome)
        uncheck_returned = False
        uncheck_threw = False
        exception_type: str | None = None
        exception_message: str | None = None
        try:
            target.uncheck(timeout=5_000)
            uncheck_returned = True
        except Exception as error:  # noqa: BLE001
            uncheck_threw = True
            exception_type = type(error).__name__
            exception_message = str(error)
            metrics.add_note(f"default_checkbox_uncheck_threw: {error}")
        immediate: bool | None = None
        immediate_enabled: bool | None = None
        try:
            immediate = bool(target.is_checked())
        except Exception:  # noqa: BLE001
            immediate = None
        try:
            immediate_enabled = bool(target.is_enabled())
        except Exception:  # noqa: BLE001
            immediate_enabled = None
        _dump(
            STAGE_AFTER_UNCHECK_RETURN_OR_THROW,
            was_checked=True,
            uncheck_attempted=True,
            uncheck_returned=uncheck_returned,
            uncheck_threw=uncheck_threw,
            uncheck_exception_type=exception_type,
            uncheck_exception_message=exception_message,
            checked_immediately_after_uncheck=immediate,
            checkbox_enabled=immediate_enabled,
        )
        started = time.monotonic()
        poll_count = 0
        last_tick = None
        while True:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            poll_count += 1
            try:
                checked = bool(target.is_checked())
            except Exception:  # noqa: BLE001
                checked = True
            try:
                enabled = bool(target.is_enabled())
            except Exception:  # noqa: BLE001
                enabled = None
            snapshot = observe_resume_snapshot(page)
            last_tick = classify_checkbox_settle_tick(
                checked=checked,
                enabled=enabled,
                current_default=snapshot.default_filename,
                default_observable=snapshot.default_observable,
                baseline_default=baseline_default_filename,
                baseline_observable=baseline_default_observable,
                application_filename=expected_cv_filename,
                elapsed_ms=elapsed_ms,
                timeout_ms=timeout_ms,
            )
            metrics.add_note(
                f"checkbox_settle poll={poll_count} checked={checked} "
                f"enabled={enabled} default={snapshot.default_filename!r} "
                f"action={last_tick.action} reason={last_tick.reason}"
            )
            _dump(
                STAGE_CHECKBOX_SETTLE_POLL,
                was_checked=True,
                uncheck_attempted=True,
                uncheck_returned=uncheck_returned,
                uncheck_threw=uncheck_threw,
                uncheck_exception_type=exception_type,
                uncheck_exception_message=exception_message,
                checked_immediately_after_uncheck=immediate,
                checkbox_enabled=enabled,
                settle_poll_index=poll_count,
                settle_poll_count=poll_count,
                settle_wait_ms=elapsed_ms,
                snapshot=snapshot,
            )
            if last_tick.action != "keep_waiting":
                break
            metrics.add_waiting(poll_ms / 1000.0)
            page.wait_for_timeout(poll_ms)
        assert last_tick is not None
        outcome = checkbox_outcome_from_settle(
            was_checked=True,
            uncheck_attempted=True,
            tick=last_tick,
            uncheck_returned=uncheck_returned,
            uncheck_threw=uncheck_threw,
            uncheck_exception_type=exception_type,
            uncheck_exception_message=exception_message,
            baseline_default=baseline_default_filename,
            poll_count=poll_count,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
        _dump(
            STAGE_CHECKBOX_GUARD_DECISION,
            was_checked=True,
            uncheck_attempted=True,
            uncheck_returned=uncheck_returned,
            uncheck_threw=uncheck_threw,
            uncheck_exception_type=exception_type,
            uncheck_exception_message=exception_message,
            checked_immediately_after_uncheck=immediate,
            checkbox_enabled=last_tick.enabled,
            settle_poll_index=poll_count,
            settle_poll_count=poll_count,
            settle_wait_ms=outcome.settle_wait_ms,
            guard=outcome,
        )
        if outcome.uncheck_succeeded:
            metrics.add_note("Unchecked Make this my default résumé after upload")
        else:
            metrics.add_failure(
                "SEEK Default checkbox/Default badge did not settle after uncheck. "
                f"reason={outcome.reason}"
            )
        metrics.add_note(f"Default résumé checkbox: {outcome.reason}")
        return _record_outcome(outcome)
    except Exception as error:  # noqa: BLE001
        metrics.add_failure(f"default_checkbox_uncheck_failed: {error}")
        outcome = evaluate_default_checkbox_guard(
            present=True,
            was_checked=True,
            still_checked=True,
            uncheck_attempted=True,
        )
        _dump(
            STAGE_CHECKBOX_GUARD_DECISION,
            was_checked=True,
            uncheck_attempted=True,
            uncheck_threw=True,
            uncheck_exception_type=type(error).__name__,
            uncheck_exception_message=str(error),
            guard=outcome,
        )
        metrics.add_note(f"Default résumé checkbox: {outcome.reason}")
        return _record_outcome(outcome)


def record_resume_snapshot(
    metrics: SpikeMetrics,
    snapshot: SeekResumeSnapshot,
    *,
    stage: str,
) -> None:
    payload = snapshot.to_metrics_dict()
    metrics.add_note(
        f"resume_snapshot[{stage}] default={snapshot.default_filename!r} "
        f"observable={snapshot.default_observable} "
        f"selected={snapshot.selected_filename!r} "
        f"count={len(snapshot.entries)}"
    )
    if stage == "before":
        metrics.default_resume_before = snapshot.default_filename
        metrics.default_observable_before = snapshot.default_observable
        metrics.selected_resume_before = snapshot.selected_filename
        metrics.resume_list_before = list(payload["entries"])  # type: ignore[arg-type]
    elif stage == "after_upload":
        metrics.default_resume_after_upload = snapshot.default_filename
        metrics.default_observable_after_upload = snapshot.default_observable
        metrics.selected_resume_after_upload = snapshot.selected_filename
        metrics.resume_list_after = list(payload["entries"])  # type: ignore[arg-type]
    elif stage == "handoff":
        metrics.default_resume_at_handoff = snapshot.default_filename
        metrics.default_observable_at_handoff = snapshot.default_observable
    if snapshot.entries:
        candidate = select_cleanup_candidate(snapshot.entries)
        metrics.cleanup_candidate = candidate.filename
        metrics.cleanup_candidate_reason = candidate.reason
        metrics.add_note(
            f"cleanup_candidate[{stage}] selected={candidate.selected} "
            f"filename={candidate.filename!r} reason={candidate.reason}"
        )


def attempt_one_resume_deletion(
    page,
    *,
    candidate_filename: str | None,
    candidate_index: int | None,
    metrics: SpikeMetrics,
    diagnostic_path: Path | None = None,
) -> str:
    """Open the candidate row's kebab and click exact Delete. No dialog guessing."""
    if candidate_index is None:
        metrics.add_note("resume_deletion status=no_candidate")
        return "no_candidate"
    gate = refuse_unobserved_resume_deletion(
        candidate_filename, candidate_index=candidate_index
    )
    if gate != "menu_observed":
        metrics.add_note(
            f"resume_deletion status={gate} candidate={candidate_filename!r} "
            f"index={candidate_index}"
        )
        return gate
    driver = PlaywrightResumeDeleteDriver(page)
    status = perform_one_resume_deletion(
        driver,
        candidate_filename=candidate_filename,
        candidate_index=candidate_index,
        diagnostic_path=diagnostic_path,
    )
    note = (
        f"resume_deletion status={status} candidate={candidate_filename!r} "
        f"index={candidate_index}"
    )
    if diagnostic_path is not None:
        note += f" diagnostic={diagnostic_path}"
    metrics.add_note(note)
    return status


class PlaywrightResumeDeleteDriver:
    """Bind Delete to the unique résumé row whose filename matches the candidate."""

    def __init__(self, page) -> None:
        self.page = page
        self._opened_index: int | None = None

    def confirmation_dialog_visible(self) -> bool:
        return self.observe_delete_confirmation().dialog_count > 0

    def observe_delete_confirmation(
        self, candidate_filename: str | None = None
    ) -> DeleteConfirmationObservation:
        dialogs = self._visible_confirm_dialogs()
        if not dialogs:
            return empty_delete_confirmation_observation()
        if len(dialogs) != 1:
            return DeleteConfirmationObservation(
                dialog_count=len(dialogs),
                prompt_present=False,
                dialog_text="",
                mentions_candidate=False,
                other_pdf_filenames=(),
                delete_action_count=0,
                cancel_action_count=0,
                extra_action_names=(),
            )
        dialog = dialogs[0]
        try:
            text = (dialog.inner_text() or "").strip()
        except Exception:  # noqa: BLE001
            text = ""
        return build_delete_confirmation_observation(
            dialog_count=1,
            dialog_text=text,
            candidate_filename=candidate_filename,
            action_names=self._dialog_action_names(dialog),
        )

    def capture_confirmation_diagnostic(
        self,
        *,
        path,
        stage: str,
        candidate_filename: str | None,
        observation: DeleteConfirmationObservation | None = None,
        plan=None,
    ) -> None:
        """Read-only DOM dump for one confirmation observe/plan. Never clicks."""
        raw_dialogs = self._raw_dialog_matches()
        detector_dialogs = self._visible_confirm_dialogs()
        controls: list[dict] = []
        raw_names: list[str] = []
        detector_names: list[str] = []
        if len(detector_dialogs) == 1:
            dialog = detector_dialogs[0]
            controls, raw_names = self._dialog_controls_dump(dialog)
            detector_names = list(self._dialog_action_names(dialog))
        if observation is None:
            observation = self.observe_delete_confirmation(candidate_filename)
        if plan is None:
            plan = plan_resume_delete_confirmation(
                candidate_filename=candidate_filename,
                observation=observation,
            )
        close_count = sum(
            1
            for name in observation.action_names_normalised
            if name == SEEK_RESUME_DELETE_CONFIRMATION_CLOSE
        )
        dismiss_count = sum(
            1
            for name in observation.action_names_normalised
            if name == SEEK_RESUME_DELETE_CONFIRMATION_DISMISS
        )
        append_confirmation_diagnostic(
            path,
            observation_diagnostic_snapshot(
                stage=stage,
                candidate_filename=candidate_filename,
                observation=observation,
                plan=plan,
                extra={
                    "dialogs": raw_dialogs,
                    "detector_dialog_count": len(detector_dialogs),
                    "controls": controls,
                    "detector_action_names": detector_names,
                    "close_action_count": close_count,
                    "dismiss_action_count": dismiss_count,
                },
            ),
        )

    def click_confirmation_delete(self) -> str:
        dialogs = self._visible_confirm_dialogs()
        if len(dialogs) != 1:
            return (
                "resume_delete_confirmation_multiple_dialogs"
                if len(dialogs) > 1
                else "resume_delete_confirmation_unobserved"
            )
        dialog = dialogs[0]
        # Dialog-scoped normalised Delete only. Never click Cancel, Dismiss, or Close.
        deletes = []
        try:
            buttons = dialog.get_by_role("button")
            for index in range(buttons.count()):
                item = buttons.nth(index)
                try:
                    if not item.is_visible():
                        continue
                    name = normalise_confirmation_action_name(
                        self._accessible_button_name(item)
                    )
                    if name == SEEK_RESUME_DELETE_ACTION:
                        deletes.append(item)
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            return "resume_delete_confirmation_unobserved"
        if len(deletes) != 1:
            return (
                "resume_delete_confirmation_multiple_delete_actions"
                if len(deletes) > 1
                else "resume_delete_confirmation_unobserved"
            )
        try:
            deletes[0].click(timeout=5_000)
        except Exception:  # noqa: BLE001
            return "delete_click_failed"
        try:
            self.page.wait_for_timeout(500)
        except Exception:  # noqa: BLE001
            pass
        return "clicked"

    def row_menus(self) -> tuple[ResumeRowMenu, ...]:
        menus: list[ResumeRowMenu] = []
        try:
            radios = self.page.get_by_role("radio")
            count = radios.count()
        except Exception:  # noqa: BLE001
            return ()
        open_actions = self._visible_menu_actions()
        visible_index = 0
        for index in range(count):
            radio = radios.nth(index)
            try:
                if not radio.is_visible():
                    continue
                text = _radio_row_text(radio)
                if should_skip_resume_radio_row(text):
                    visible_index += 1
                    continue
                filename = extract_pdf_filename(text)
                if not filename:
                    visible_index += 1
                    continue
                info = radio.evaluate(_ROW_OVERFLOW_INFO_JS)
                overflow_count = int((info or {}).get("count") or 0)
                expanded = bool((info or {}).get("expanded"))
            except Exception:  # noqa: BLE001
                visible_index += 1
                continue
            opened_here = self._opened_index == visible_index
            menu_open = expanded or opened_here
            menus.append(
                ResumeRowMenu(
                    filename=filename,
                    index=visible_index,
                    is_default=row_is_structurally_default(text),
                    overflow_control_count=overflow_count,
                    menu_open=menu_open,
                    menu_actions=open_actions if menu_open else (),
                )
            )
            visible_index += 1
        return tuple(menus)

    def open_overflow(self, row_index: int) -> str:
        radio = self._radio_at_visible_index(row_index)
        if isinstance(radio, str):
            return radio
        text = _radio_row_text(radio)
        if row_is_structurally_default(text):
            return "default_row_protected"
        try:
            result = radio.evaluate(_CLICK_ROW_OVERFLOW_JS)
        except Exception:  # noqa: BLE001
            return "overflow_click_failed"
        status = str(result or "overflow_not_found_on_row")
        if status == "opened":
            self._opened_index = row_index
            try:
                self.page.wait_for_timeout(400)
            except Exception:  # noqa: BLE001
                pass
        return status

    def click_exact_delete(self) -> str:
        locators = []
        try:
            items = self.page.get_by_role(
                "menuitem", name=SEEK_RESUME_DELETE_ACTION, exact=True
            )
            locators.append(items)
        except Exception:  # noqa: BLE001
            pass
        try:
            menu = self.page.get_by_role("menu")
            if menu.count() == 1 and menu.first.is_visible():
                locators.append(
                    menu.first.get_by_role(
                        "button", name=SEEK_RESUME_DELETE_ACTION, exact=True
                    )
                )
        except Exception:  # noqa: BLE001
            pass
        visible = []
        for loc in locators:
            try:
                for index in range(loc.count()):
                    item = loc.nth(index)
                    if item.is_visible():
                        visible.append(item)
            except Exception:  # noqa: BLE001
                continue
        if len(visible) != 1:
            return (
                "menu_association_ambiguous"
                if len(visible) > 1
                else "delete_action_not_visible"
            )
        try:
            visible[0].click(timeout=5_000)
        except Exception:  # noqa: BLE001
            return "delete_click_failed"
        try:
            self.page.wait_for_timeout(500)
        except Exception:  # noqa: BLE001
            pass
        return "clicked"

    def _visible_confirm_dialogs(self) -> list:
        found: list = []
        texts: list[str] = []
        for role in ("alertdialog", "dialog"):
            try:
                loc = self.page.get_by_role(role)
                count = loc.count()
            except Exception:  # noqa: BLE001
                continue
            for index in range(count):
                dialog = loc.nth(index)
                try:
                    if not dialog.is_visible():
                        continue
                    text = (dialog.inner_text() or "").strip()
                except Exception:  # noqa: BLE001
                    continue
                if text in texts:
                    continue
                texts.append(text)
                found.append(dialog)
        return found

    def _raw_dialog_matches(self) -> list[dict]:
        matches: list[dict] = []
        for role in ("alertdialog", "dialog"):
            try:
                loc = self.page.get_by_role(role)
                count = loc.count()
            except Exception:  # noqa: BLE001
                continue
            for index in range(count):
                dialog = loc.nth(index)
                visible = False
                text = ""
                try:
                    visible = bool(dialog.is_visible())
                except Exception:  # noqa: BLE001
                    visible = False
                if visible:
                    try:
                        text = (dialog.inner_text() or "").strip()
                    except Exception:  # noqa: BLE001
                        text = ""
                matches.append(
                    {
                        "role": role,
                        "index": index,
                        "visible": visible,
                        "inner_text": text,
                    }
                )
        return matches

    def _dialog_controls_dump(self, dialog) -> tuple[list[dict], list[str]]:
        controls: list[dict] = []
        raw_names: list[str] = []
        for role in ("button", "link", "menuitem"):
            try:
                loc = dialog.get_by_role(role)
                count = loc.count()
            except Exception:  # noqa: BLE001
                continue
            for index in range(count):
                item = loc.nth(index)
                try:
                    visible = bool(item.is_visible())
                except Exception:  # noqa: BLE001
                    continue
                if not visible:
                    continue
                try:
                    aria = (item.get_attribute("aria-label") or "").strip()
                except Exception:  # noqa: BLE001
                    aria = ""
                try:
                    inner = (item.inner_text() or "").strip()
                except Exception:  # noqa: BLE001
                    inner = ""
                accessible = confirmation_accessible_name(
                    aria_label=aria, inner_text=inner
                )
                controls.append(
                    {
                        "role": role,
                        "aria_label": aria,
                        "accessible_name": accessible,
                        "inner_text": inner,
                        "visible": True,
                    }
                )
                if role == "button":
                    raw_names.append(accessible)
        return controls, raw_names

    def _dialog_action_names(self, dialog) -> tuple[str, ...]:
        names: list[str] = []
        try:
            buttons = dialog.get_by_role("button")
            for index in range(buttons.count()):
                item = buttons.nth(index)
                try:
                    if not item.is_visible():
                        continue
                    names.append(self._accessible_button_name(item))
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            return tuple(names)
        return tuple(name for name in names if name)

    def _accessible_button_name(self, item) -> str:
        """Prefer accessible name; do not identify Delete by inner_text alone."""
        try:
            aria = (item.get_attribute("aria-label") or "").strip()
        except Exception:  # noqa: BLE001
            aria = ""
        inner = ""
        if not aria:
            try:
                inner = item.evaluate(
                    """el => (el.innerText || '').replace(/\\s+/g, ' ').trim()"""
                )
            except Exception:  # noqa: BLE001
                try:
                    inner = (item.inner_text() or "").strip()
                except Exception:  # noqa: BLE001
                    inner = ""
            if not isinstance(inner, str):
                inner = ""
        return confirmation_accessible_name(aria_label=aria, inner_text=inner)

    def _radio_at_visible_index(self, row_index: int):
        try:
            radios = self.page.get_by_role("radio")
            count = radios.count()
        except Exception:  # noqa: BLE001
            return "row_not_found"
        visible_index = 0
        for index in range(count):
            radio = radios.nth(index)
            try:
                if not radio.is_visible():
                    continue
            except Exception:  # noqa: BLE001
                continue
            if visible_index == row_index:
                return radio
            visible_index += 1
        return "row_not_found"

    def _visible_menu_actions(self) -> tuple[str, ...]:
        names: list[str] = []
        try:
            items = self.page.get_by_role("menuitem")
            for index in range(items.count()):
                item = items.nth(index)
                try:
                    if item.is_visible():
                        names.append((item.inner_text() or "").strip())
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            return tuple(n for n in names if n)
        if names:
            return tuple(n for n in names if n)
        try:
            menu = self.page.get_by_role("menu")
            if menu.count() != 1 or not menu.first.is_visible():
                return ()
            buttons = menu.first.get_by_role("button")
            for index in range(buttons.count()):
                button = buttons.nth(index)
                try:
                    if button.is_visible():
                        names.append((button.inner_text() or "").strip())
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            return ()
        return tuple(n for n in names if n)


def observe_resume_capacity_response(page) -> str | None:
    """Return SEEK résumé-capacity evidence, or None if the library is not full."""
    body = page_body_text(page)
    matched = detect_resume_capacity_message(body)
    if matched:
        return matched
    try:
        loc = page.get_by_text(re.compile(r"r[eé]sum[eé]\s+limit\s+reached", re.I))
        if loc.count() > 0 and loc.first.is_visible():
            return "Résumé limit reached"
    except Exception:  # noqa: BLE001
        pass
    return None


def dismiss_resume_capacity_modal_without_deleting(page) -> bool:
    """Close the capacity dialog without clicking Delete."""
    for pattern in (
        re.compile(r"^(dismiss|close)$", re.I),
        re.compile(r"dismiss", re.I),
    ):
        try:
            buttons = page.get_by_role("button", name=pattern)
            for index in range(min(buttons.count(), 6)):
                button = buttons.nth(index)
                try:
                    name = normalise_confirmation_action_name(
                        button.get_attribute("aria-label") or button.inner_text() or ""
                    )
                except Exception:  # noqa: BLE001
                    name = ""
                if re.search(r"delete", name or "", re.I):
                    continue
                if button.is_visible() and button.is_enabled():
                    button.click(timeout=3_000)
                    page.wait_for_timeout(400)
                    return True
        except Exception:  # noqa: BLE001
            continue
    return False


def describe_resume_upload_association(element) -> dict[str, Any]:
    """Describe how the visible Upload control is tied to ``#resume-fileFile``."""
    try:
        described = element.evaluate(_DESCRIBE_ASSOCIATION_JS)
        if isinstance(described, dict) and described.get("method"):
            described.setdefault("found", True)
            return described
    except Exception:  # noqa: BLE001
        pass
    name = ""
    try:
        label = element.get_attribute("aria-label") or ""
        inner = element.inner_text() or ""
        name = normalise_upload_accessible_name(f"{label} {inner}")
    except Exception:  # noqa: BLE001
        name = ""
    return {
        "found": True,
        "method": "resume-fileFile_associated_upload",
        "accessible_name": name,
    }


def locate_associated_resume_upload_button(page) -> tuple[Any | None, dict[str, Any]]:
    """Return the résumé Upload control associated with ``#resume-fileFile``.

    Does not use ``get_by_role("button", name="Upload").first``.
    """
    try:
        handle = page.evaluate_handle(_FIND_RESUME_UPLOAD_BUTTON_JS)
        element = handle.as_element() if handle is not None else None
    except Exception:  # noqa: BLE001
        element = None
    if element is None:
        return None, {
            "found": False,
            "method": None,
            "note": (
                "No Upload button in a container with #resume-fileFile "
                "excluding cover-letter inputs"
            ),
        }
    return element, describe_resume_upload_association(element)


def ensure_saved_resume_selected_for_upload(page, metrics: SpikeMetrics) -> bool:
    """Leave a valid saved résumé selected, or select one non-Default saved row.

    Never selects "Don't include a résumé", cover-letter radios, or Default
    as a special preference.
    """
    snapshot = observe_resume_snapshot(page)
    if snapshot.selected_filename:
        metrics.add_note(
            "resume_preselect_left_selected="
            f"{snapshot.selected_filename!r}"
        )
        return True
    candidates = [
        entry
        for entry in snapshot.entries
        if entry.filename and not entry.is_default
    ]
    if not candidates:
        metrics.add_note("resume_preselect_no_non_default_saved_resume")
        return False
    target = candidates[0].filename
    clicked = click_resume_radio_by_filename(page, target)
    metrics.add_note(
        f"resume_preselect_clicked={clicked} target={target!r}"
    )
    page.wait_for_timeout(400)
    after = observe_resume_snapshot(page)
    if after.selected_filename:
        metrics.add_note(
            "resume_preselect_selected="
            f"{after.selected_filename!r}"
        )
        return True
    return False


def _upload_resume_via_filechooser(
    page,
    *,
    cv_pdf: Path,
    metrics: SpikeMetrics,
    dump,
    already_cv_skip: bool,
    count_zero_skip: bool,
    default_before_upload: str | None,
    association: Mapping[str, Any],
    resume_button,
    expected_cv_present_before_upload: bool = False,
    saved_resume_count: int | None = None,
) -> None:
    """Click associated résumé Upload and set files on the filechooser.

    Never falls back to hidden-input ``set_input_files``.
    """
    filechooser_event_observed = False
    chooser_set_files_started = False
    chooser_set_files_returned = False
    chooser_set_files_threw = False
    exception_type: str | None = None
    exception_message: str | None = None

    def _fields(**extra: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "already_cv_skip": already_cv_skip,
            "resume_input_count_zero_skip": count_zero_skip,
            "upload_interaction": UPLOAD_INTERACTION_FILECHOOSER,
            "resume_upload_association": dict(association),
            "chosen_via": CHOSEN_VIA_RESUME_FILE_ASSOCIATED_UPLOAD,
            "filechooser_event_observed": filechooser_event_observed,
            "chooser_set_files_started": chooser_set_files_started,
            "chooser_set_files_returned": chooser_set_files_returned,
            "chooser_set_files_threw": chooser_set_files_threw,
            "chooser_set_files_exception_type": exception_type,
            "chooser_set_files_exception_message": exception_message,
            "default_before_upload": default_before_upload,
            "upload_attempted": True,
            "capacity_modal_observed": False,
            "existing_expected_cv_reused": False,
            "expected_cv_present_before_upload": expected_cv_present_before_upload,
            "saved_resume_count": saved_resume_count,
            "set_input_files_started": False,
            "set_input_files_returned": False,
            "set_input_files_threw": False,
        }
        payload.update(extra)
        return payload

    try:
        with page.expect_file_chooser(timeout=FILECHOOSER_TIMEOUT_MS) as pending:
            resume_button.click(timeout=5_000)
        chooser = getattr(pending, "value", None)
        if chooser is None:
            raise TimeoutError("filechooser event did not occur")
        filechooser_event_observed = True
    except ResumeUploadInteractionError:
        raise
    except Exception as error:  # noqa: BLE001
        exception_type = type(error).__name__
        exception_message = str(error)
        capacity = observe_resume_capacity_response(page)
        if capacity:
            dismiss_resume_capacity_modal_without_deleting(page)
            dump(
                **_fields(
                    upload_interaction=UPLOAD_INTERACTION_CAPACITY,
                    capacity_modal_observed=True,
                )
            )
            metrics.resume_capacity_blocked = True
            metrics.resume_capacity_evidence = capacity
            metrics.upload_failure_reason = "resume_capacity_blocked"
            metrics.add_failure(f"resume_capacity_blocked: {capacity}")
            raise ResumeUploadInteractionError(
                "resume_capacity_blocked",
                f"SEEK résumé library is full ({capacity}); no filechooser.",
            ) from error
        dump(**_fields())
        metrics.upload_failure_reason = "no_filechooser_event"
        metrics.add_failure(f"resume_upload_interaction:no_filechooser_event: {error}")
        raise ResumeUploadInteractionError(
            "no_filechooser_event",
            f"Résumé Upload produced neither a filechooser nor a capacity response: {error}",
        ) from error

    try:
        chooser_set_files_started = True
        chooser.set_files(str(cv_pdf))
        chooser_set_files_returned = True
    except Exception as error:  # noqa: BLE001
        chooser_set_files_threw = True
        exception_type = type(error).__name__
        exception_message = str(error)
        dump(**_fields())
        metrics.upload_failure_reason = "chooser_set_files_threw"
        metrics.add_failure(f"resume_upload_interaction:chooser_set_files_threw: {error}")
        raise ResumeUploadInteractionError(
            "chooser_set_files_threw",
            f"chooser.set_files failed: {error}",
        ) from error

    dump(**_fields())


def prepare_and_upload_documents(
    page,
    *,
    cv_pdf: Path,
    cl_pdf: Path,
    metrics: SpikeMetrics,
    retry_cv: bool = False,
    upload_diagnostic_path: Path | str | None = None,
) -> bool:
    """Upload CV/CL only after cover-letter method radio is verified when present."""
    try:
        assert_safe_external_upload_pdf(cv_pdf, kind="cv", must_exist=True)
        assert_safe_external_upload_pdf(cl_pdf, kind="cover_letter", must_exist=True)
    except UnsafeUploadArtefactError as error:
        metrics.add_failure(str(error))
        raise

    uploaded_any = False
    radios_present = cover_letter_method_radios_present(page)
    if radios_present:
        checked = select_cover_letter_upload_method(page, metrics)
        try:
            assert_cover_letter_radio_checked(checked)
        except CoverLetterGateError as error:
            metrics.add_failure(str(error))
            return False
        cover_inputs = cover_letter_file_input(page)
        try:
            if cover_inputs.count() == 0:
                metrics.add_failure(
                    "Cover-letter file input not available after radio selection"
                )
                return False
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"cover_letter_input_probe_failed: {error}")
            return False

    stage_before = STAGE_RETRY_UPLOAD_BEFORE if retry_cv else STAGE_FIRST_UPLOAD_BEFORE
    stage_after = STAGE_RETRY_UPLOAD_AFTER if retry_cv else STAGE_FIRST_UPLOAD_AFTER

    def _dump_upload(stage: str, **fields: object) -> None:
        capture_upload_observation(
            page,
            path=upload_diagnostic_path,
            stage=stage,
            expected_cv_path=str(cv_pdf),
            expected_cv_filename=cv_pdf.name,
            retry_cv=retry_cv,
            **fields,
        )

    # Résumé: reuse exact saved expected CV, else visible Upload + filechooser.
    already_cv = (not retry_cv) and any(
        item.startswith("cv:") for item in metrics.documents_uploaded
    )
    resume_inputs = resume_file_input(page)
    resume_count = 0
    try:
        resume_count = resume_inputs.count()
    except Exception:  # noqa: BLE001
        resume_count = 0
    already_cv_skip = bool(resume_count > 0 and already_cv)
    count_zero_skip = bool(resume_count == 0)
    baseline_snapshot = observe_resume_snapshot(page)
    default_before_upload = baseline_snapshot.default_filename
    expected_present_before = snapshot_has_filename(baseline_snapshot, cv_pdf.name)
    saved_count = len(baseline_snapshot.entries)
    _dump_upload(
        stage_before,
        already_cv_skip=already_cv_skip,
        resume_input_count_zero_skip=count_zero_skip,
        default_before_upload=default_before_upload,
        expected_cv_present_before_upload=expected_present_before,
        saved_resume_count=saved_count,
        upload_attempted=False,
        existing_expected_cv_reused=False,
        capacity_modal_observed=False,
        set_input_files_started=False,
        set_input_files_returned=False,
        set_input_files_threw=False,
    )
    if expected_present_before:
        if not filenames_equal(baseline_snapshot.selected_filename, cv_pdf.name):
            click_resume_radio_by_filename(page, cv_pdf.name)
            page.wait_for_timeout(400)
        after_reuse = observe_resume_snapshot(page)
        reused = filenames_equal(after_reuse.selected_filename, cv_pdf.name)
        _dump_upload(
            stage_after,
            already_cv_skip=False,
            resume_input_count_zero_skip=False,
            default_before_upload=default_before_upload,
            upload_interaction=UPLOAD_INTERACTION_EXISTING_REUSED,
            chosen_via=CHOSEN_VIA_EXISTING_SAVED_RESUME,
            expected_cv_present_before_upload=True,
            saved_resume_count=saved_count,
            upload_attempted=False,
            existing_expected_cv_reused=reused,
            filechooser_event_observed=False,
            capacity_modal_observed=False,
            set_input_files_started=False,
            set_input_files_returned=False,
            set_input_files_threw=False,
        )
        if reused:
            metrics.documents_uploaded.append(f"cv:{cv_pdf.name}")
            metrics.record_field(
                "upload:resume",
                "auto",
                detail="existing_expected_cv_reused",
                value_preview=cv_pdf.name,
            )
            uploaded_any = True
            metrics.add_note(
                "existing_expected_cv_reused "
                f"filename={cv_pdf.name!r} "
                f"saved_count={saved_count} "
                f"selected={after_reuse.selected_filename!r}"
            )
        else:
            metrics.add_note(
                "expected_cv_present_but_not_selected "
                f"observed={after_reuse.selected_filename!r}"
            )
    elif resume_count > 0 and already_cv:
        metrics.add_note("Skipping resume re-upload; CV already uploaded this run")
        _dump_upload(
            stage_after,
            already_cv_skip=True,
            resume_input_count_zero_skip=False,
            default_before_upload=default_before_upload,
            expected_cv_present_before_upload=expected_present_before,
            saved_resume_count=saved_count,
            upload_attempted=False,
            set_input_files_started=False,
            set_input_files_returned=False,
            set_input_files_threw=False,
        )
    elif resume_count > 0:
        if not ensure_saved_resume_selected_for_upload(page, metrics):
            _dump_upload(
                stage_after,
                already_cv_skip=False,
                resume_input_count_zero_skip=False,
                default_before_upload=default_before_upload,
                upload_interaction=UPLOAD_INTERACTION_FILECHOOSER,
                filechooser_event_observed=False,
                chooser_set_files_started=False,
                chooser_set_files_returned=False,
                chooser_set_files_threw=False,
                set_input_files_started=False,
                set_input_files_returned=False,
                set_input_files_threw=False,
            )
            metrics.upload_failure_reason = "no_saved_resume_selected_for_upload"
            metrics.add_failure(
                "resume_upload_interaction:no_saved_resume_selected_for_upload"
            )
            raise ResumeUploadInteractionError(
                "no_saved_resume_selected_for_upload",
                "No saved résumé was selected before Upload; "
                "will not use Don't include a résumé or Default as a preference.",
            )
        resume_button, association = locate_associated_resume_upload_button(page)
        if resume_button is None:
            _dump_upload(
                stage_after,
                already_cv_skip=False,
                resume_input_count_zero_skip=False,
                default_before_upload=default_before_upload,
                upload_interaction=UPLOAD_INTERACTION_FILECHOOSER,
                resume_upload_association=association,
                filechooser_event_observed=False,
                chooser_set_files_started=False,
                chooser_set_files_returned=False,
                chooser_set_files_threw=False,
                set_input_files_started=False,
                set_input_files_returned=False,
                set_input_files_threw=False,
            )
            metrics.upload_failure_reason = "resume_upload_button_not_associated"
            metrics.add_failure(
                "resume_upload_interaction:resume_upload_button_not_associated"
            )
            raise ResumeUploadInteractionError(
                "resume_upload_button_not_associated",
                "Could not associate a visible Upload control with #resume-fileFile.",
            )
        _upload_resume_via_filechooser(
            page,
            cv_pdf=cv_pdf,
            metrics=metrics,
            dump=lambda **fields: _dump_upload(stage_after, **fields),
            already_cv_skip=False,
            count_zero_skip=False,
            default_before_upload=default_before_upload,
            association=association,
            resume_button=resume_button,
            expected_cv_present_before_upload=expected_present_before,
            saved_resume_count=saved_count,
        )
        metrics.documents_uploaded.append(f"cv:{cv_pdf.name}")
        metrics.record_field(
            "upload:resume",
            "auto",
            detail="cv",
            value_preview=cv_pdf.name,
        )
        uploaded_any = True
        metrics.add_note(
            f"{'Retried' if retry_cv else 'Uploaded'} cv via résumé Upload filechooser: "
            f"{cv_pdf.name}"
        )
        page.wait_for_timeout(200)
    else:
        _dump_upload(
            stage_after,
            already_cv_skip=False,
            resume_input_count_zero_skip=True,
            default_before_upload=default_before_upload,
            set_input_files_started=False,
            set_input_files_returned=False,
            set_input_files_threw=False,
        )

    if radios_present:
        already_cl = any(
            item.startswith("cover_letter:") for item in metrics.documents_uploaded
        )
        if already_cl:
            metrics.add_note(
                "Skipping cover-letter re-upload; already uploaded this run"
            )
            return uploaded_any
        cover_inputs = cover_letter_file_input(page)
        try:
            cover_inputs.first.set_input_files(str(cl_pdf))
            page.wait_for_timeout(1000)
            if not cover_letter_filename_visible(page, cl_pdf.name):
                # Some SEEK UIs show a generic "Cover letter uploaded" without filename.
                body = page_body_text(page).lower()
                if "cover letter" not in body:
                    metrics.add_failure(
                        f"Cover-letter PDF not visible after upload: {cl_pdf.name}"
                    )
                    return uploaded_any
            metrics.documents_uploaded.append(f"cover_letter:{cl_pdf.name}")
            metrics.record_field(
                "upload:cover_letter",
                "auto",
                detail="cover_letter",
                value_preview=cl_pdf.name,
            )
            uploaded_any = True
            metrics.add_note(f"Uploaded cover_letter via cover input: {cl_pdf.name}")
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"upload_failed[cover_letter]: {error}")
            return uploaded_any

    return uploaded_any


def documents_step_ready_to_continue(
    page,
    *,
    expected_cv_filename: str,
    snapshot: SeekResumeSnapshot,
    spinner_active: bool,
) -> None:
    """Refuse Continue unless expected CV is selected and cover letter is ready.

    Default résumé state is a separate invariant and cannot compensate.
    """
    if spinner_active:
        raise DocumentsStepGateError(
            "resume_upload_still_processing",
            "Résumé upload is still processing; refusing Continue.",
        )
    cv_gate = evaluate_expected_cv_selection(
        snapshot, expected_cv_filename, spinner_active=False
    )
    if not cv_gate.selected:
        raise DocumentsStepGateError(
            cv_gate.reason,
            "Expected CV is not the selected application résumé: "
            f"expected={expected_cv_filename!r} "
            f"observed={cv_gate.observed_selected!r} "
            f"reason={cv_gate.reason}",
        )
    if application_cv_is_structural_default(
        default_filename=snapshot.default_filename,
        expected_filename=expected_cv_filename,
    ):
        raise DocumentsStepGateError(
            "expected_cv_is_structural_default",
            "Expected application CV is the structural Default; "
            "automation will not Continue and will not restore Default "
            "by selecting another résumé. Restore the protected generic "
            f"Default in SEEK, leaving {expected_cv_filename!r} selected.",
        )
    body = page_body_text(page)
    messages = detect_validation_messages(body)
    radios_present = cover_letter_method_radios_present(page)
    checked = (
        is_cover_letter_upload_radio_checked(page) if radios_present else True
    )
    assert_may_continue_documents_step(
        radio_checked=checked,
        validation_messages=messages,
    )


def refuse_default_checkbox_activation(label: str | None) -> bool:
    """True when a control/label must not be activated as field assist."""
    return is_default_resume_checkbox_label(label)
