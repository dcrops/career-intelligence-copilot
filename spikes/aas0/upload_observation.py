"""Read-only résumé upload / retry diagnostic dump (AAS-0.1).

Live résumé upload uses visible Upload + Playwright filechooser. Historical
hidden-input ``set_input_files`` fields remain for compatibility. Live capture
lives in ``seek_documents``.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence
from pathlib import Path

_WORD_JOINER = "\u2060"
_UPLOAD_NAME = re.compile(r"^upload$", re.I)

STAGE_FIRST_UPLOAD_BEFORE = "first_upload_before"
STAGE_FIRST_UPLOAD_AFTER = "first_upload_after_filechooser"
STAGE_FIRST_CV_WAIT_INITIAL = "first_cv_wait_initial"
STAGE_FIRST_CV_WAIT_FINAL = "first_cv_wait_final"
STAGE_RETRY_UPLOAD_BEFORE = "retry_upload_before"
STAGE_RETRY_UPLOAD_AFTER = "retry_upload_after_filechooser"
STAGE_RETRY_CV_WAIT_INITIAL = "retry_cv_wait_initial"
STAGE_RETRY_CV_WAIT_FINAL = "retry_cv_wait_final"

# Historical dump stage names from hidden-input résumé injection.
STAGE_FIRST_UPLOAD_AFTER_HIDDEN_INPUT = "first_upload_after_set_input_files"
STAGE_RETRY_UPLOAD_AFTER_HIDDEN_INPUT = "retry_upload_after_set_input_files"

CHOSEN_VIA_LOCATOR_FIRST = "locator.first"
CHOSEN_VIA_RESUME_FILE_ASSOCIATED_UPLOAD = "resume-fileFile_associated_upload"
CHOSEN_VIA_EXISTING_SAVED_RESUME = "existing_saved_resume"
UPLOAD_INTERACTION_FILECHOOSER = "filechooser"
UPLOAD_INTERACTION_EXISTING_REUSED = "existing_expected_cv_reused"
UPLOAD_INTERACTION_CAPACITY = "resume_capacity_blocked"
UPLOAD_INTERACTION_COVER_LETTER_HIDDEN_INPUT = "cover_letter_hidden_input"

UPLOAD_OBSERVATION_FILENAME = "upload_observation.json"

_INPUT_KEYS = (
    "index",
    "tag_name",
    "input_type",
    "visible",
    "enabled",
    "attached",
    "id",
    "name",
    "aria_label",
    "data_automation",
    "bounding_box",
)

_UPLOAD_CONTROL_KEYS = (
    "index",
    "accessible_name",
    "aria_busy",
    "role",
    "visible",
    "enabled",
    "inner_text",
    "class_name",
    "svg_classes",
    "progressbar_count",
    "aria_busy_child_count",
    "spin_or_loading_count",
)


def normalise_upload_accessible_name(value: str | None) -> str:
    """Strip SEEK WORD JOINER / NBSP so Upload matches the visible control name."""
    text = (value or "").replace(_WORD_JOINER, " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def is_resume_upload_accessible_name(value: str | None) -> bool:
    return bool(_UPLOAD_NAME.fullmatch(normalise_upload_accessible_name(value)))


def normalise_file_input_match(raw: Mapping[str, Any] | None, *, index: int) -> dict[str, Any]:
    source = dict(raw or {})
    match: dict[str, Any] = {"index": index}
    for key in _INPUT_KEYS:
        if key == "index":
            continue
        match[key] = source.get(key)
    return match


def normalise_upload_control(raw: Mapping[str, Any] | None, *, index: int) -> dict[str, Any]:
    source = dict(raw or {})
    control: dict[str, Any] = {"index": index}
    for key in _UPLOAD_CONTROL_KEYS:
        if key == "index":
            continue
        control[key] = source.get(key)
    return control


def build_upload_observation_snapshot(
    *,
    stage: str,
    expected_cv_path: str | None = None,
    expected_cv_filename: str | None = None,
    retry_cv: bool | None = None,
    resume_input_matches: Sequence[Mapping[str, Any]] | None = None,
    chosen_index: int | None = None,
    chosen_via: str | None = None,
    cover_letter_input_count: int | None = None,
    cover_letter_radio_checked: bool | None = None,
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
    set_input_files_started: bool | None = None,
    set_input_files_returned: bool | None = None,
    set_input_files_threw: bool | None = None,
    set_input_files_exception_type: str | None = None,
    set_input_files_exception_message: str | None = None,
    spinner_detector: bool | None = None,
    upload_button_aria_busy: bool | None = None,
    upload_control_has_progress: bool | None = None,
    uploading_text_visible: bool | None = None,
    upload_controls: Sequence[Mapping[str, Any]] | None = None,
    resume_filenames: Sequence[str] | None = None,
    selected_filename: str | None = None,
    structural_default_filename: str | None = None,
    expected_cv_present: bool | None = None,
    expected_cv_selected: bool | None = None,
    cv_wait_action: str | None = None,
    cv_wait_reason: str | None = None,
    expected_cv_present_before_upload: bool | None = None,
    saved_resume_count: int | None = None,
    upload_attempted: bool | None = None,
    capacity_modal_observed: bool | None = None,
    existing_expected_cv_reused: bool | None = None,
) -> dict[str, Any]:
    """Serialize one diagnostic stage. Does not decide STOP or retry."""
    inputs = [
        normalise_file_input_match(item, index=int(item.get("index", index)))
        for index, item in enumerate(resume_input_matches or ())
    ]
    controls = [
        normalise_upload_control(item, index=int(item.get("index", index)))
        for index, item in enumerate(upload_controls or ())
    ]
    return {
        "stage": stage,
        "retry_cv": retry_cv,
        "expected_cv_path": expected_cv_path,
        "expected_cv_filename": expected_cv_filename,
        "match_count": len(inputs),
        "chosen_index": chosen_index,
        "chosen_via": chosen_via,
        "resume_inputs": inputs,
        "cover_letter_input_count": cover_letter_input_count,
        "cover_letter_radio_checked": cover_letter_radio_checked,
        "already_cv_skip": already_cv_skip,
        "resume_input_count_zero_skip": resume_input_count_zero_skip,
        "upload_interaction": upload_interaction,
        "resume_upload_association": (
            dict(resume_upload_association) if resume_upload_association else None
        ),
        "filechooser_event_observed": filechooser_event_observed,
        "chooser_set_files_started": chooser_set_files_started,
        "chooser_set_files_returned": chooser_set_files_returned,
        "chooser_set_files_threw": chooser_set_files_threw,
        "chooser_set_files_exception_type": chooser_set_files_exception_type,
        "chooser_set_files_exception_message": chooser_set_files_exception_message,
        "upload_settle_elapsed_ms": upload_settle_elapsed_ms,
        "default_before_upload": default_before_upload,
        "default_after_upload": default_after_upload,
        "default_after_uncheck_settle": default_after_uncheck_settle,
        "set_input_files_started": set_input_files_started,
        "set_input_files_returned": set_input_files_returned,
        "set_input_files_threw": set_input_files_threw,
        "set_input_files_exception_type": set_input_files_exception_type,
        "set_input_files_exception_message": set_input_files_exception_message,
        "spinner_detector": spinner_detector,
        "upload_button_aria_busy": upload_button_aria_busy,
        "upload_control_has_progress": upload_control_has_progress,
        "uploading_text_visible": uploading_text_visible,
        "upload_controls": controls,
        "resume_filenames": list(resume_filenames or ()),
        "selected_filename": selected_filename,
        "structural_default_filename": structural_default_filename,
        "expected_cv_present": expected_cv_present,
        "expected_cv_selected": expected_cv_selected,
        "cv_wait_action": cv_wait_action,
        "cv_wait_reason": cv_wait_reason,
        "expected_cv_present_before_upload": expected_cv_present_before_upload,
        "saved_resume_count": saved_resume_count,
        "upload_attempted": upload_attempted,
        "capacity_modal_observed": capacity_modal_observed,
        "existing_expected_cv_reused": existing_expected_cv_reused,
    }


def append_upload_diagnostic(path: Path | str, snapshot: Mapping[str, Any]) -> None:
    """Write/append a stage snapshot before owner-session teardown."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"snapshots": []}
    if target.exists():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("snapshots"), list):
                payload = loaded
        except Exception:  # noqa: BLE001
            payload = {"snapshots": []}
    payload["snapshots"].append(dict(snapshot))
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def diagnostic_has_stage(path: Path | str, stage: str) -> bool:
    target = Path(path)
    if not target.exists():
        return False
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(loaded, dict) or not isinstance(loaded.get("snapshots"), list):
        return False
    return any(
        isinstance(item, dict) and item.get("stage") == stage
        for item in loaded["snapshots"]
    )
