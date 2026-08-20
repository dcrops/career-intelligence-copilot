"""Read-only Default-checkbox / Default-badge diagnostic dump (AAS-0.1).

Measurement only. Does not choose the checkbox, uncheck it, restore Default,
or change STOP policy. Live capture lives in ``seek_documents``.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence
from pathlib import Path

STAGE_BEFORE_DOCUMENT_UPLOAD = "before_document_upload"
STAGE_AFTER_EXPECTED_CV_APPEARS = "after_expected_cv_appears"
STAGE_BEFORE_UNCHECK = "before_uncheck"
STAGE_AFTER_UNCHECK_RETURN_OR_THROW = "after_uncheck_return_or_throw"
STAGE_AFTER_400MS_WAIT = "after_400ms_wait"
STAGE_CHECKBOX_SETTLE_POLL = "checkbox_settle_poll"
STAGE_CHECKBOX_GUARD_DECISION = "checkbox_guard_decision"
STAGE_STRUCTURAL_DEFAULT_REOBSERVED = "structural_default_reobserved"

LOCATOR_EXACT_NAME = "exact_name"
LOCATOR_REGEX_FALLBACK = "regex_fallback"

CHOSEN_VIA_LOCATOR_FIRST = "locator.first"

DEFAULT_CHECKBOX_OBSERVATION_FILENAME = "default_checkbox_observation.json"

_MATCH_KEYS = (
    "index",
    "tag_name",
    "input_type",
    "role",
    "accessible_name",
    "aria_label",
    "visible",
    "enabled",
    "is_checked",
    "checked_attribute",
    "checked_property",
    "aria_checked",
    "wrapper_tag",
    "wrapper_class",
    "wrapper_role",
    "wrapper_data_automation",
)


def normalise_checkbox_match(raw: Mapping[str, Any] | None, *, index: int) -> dict[str, Any]:
    """Stable per-match schema. Missing fields are null, never invented as false."""
    source = dict(raw or {})
    match: dict[str, Any] = {"index": index}
    for key in _MATCH_KEYS:
        if key == "index":
            continue
        match[key] = source.get(key)
    return match


def build_default_checkbox_observation_snapshot(
    *,
    stage: str,
    locator_source: str,
    matches: Sequence[Mapping[str, Any]] | None = None,
    chosen_index: int | None = None,
    chosen_via: str | None = None,
    structural_default_filename: str | None = None,
    selected_filename: str | None = None,
    expected_cv_filename: str | None = None,
    expected_cv_present: bool | None = None,
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
    guard_reason: str | None = None,
    guard_should_stop: bool | None = None,
    guard_uncheck_succeeded: bool | None = None,
) -> dict[str, Any]:
    """Serialize one diagnostic stage. Does not decide STOP."""
    normalised = [
        normalise_checkbox_match(item, index=int(item.get("index", index)))
        for index, item in enumerate(matches or ())
    ]
    return {
        "stage": stage,
        "locator_source": locator_source,
        "match_count": len(normalised),
        "chosen_index": chosen_index,
        "chosen_via": chosen_via,
        "matches": normalised,
        "structural_default_filename": structural_default_filename,
        "selected_filename": selected_filename,
        "expected_cv_filename": expected_cv_filename,
        "expected_cv_present": expected_cv_present,
        "was_checked": was_checked,
        "uncheck_attempted": uncheck_attempted,
        "uncheck_returned": uncheck_returned,
        "uncheck_threw": uncheck_threw,
        "uncheck_exception_type": uncheck_exception_type,
        "uncheck_exception_message": uncheck_exception_message,
        "checked_immediately_after_uncheck": checked_immediately_after_uncheck,
        "checked_after_400ms_wait": checked_after_400ms_wait,
        "checkbox_enabled": checkbox_enabled,
        "baseline_default_filename": baseline_default_filename,
        "settle_poll_index": settle_poll_index,
        "settle_poll_count": settle_poll_count,
        "settle_wait_ms": settle_wait_ms,
        "guard_reason": guard_reason,
        "guard_should_stop": guard_should_stop,
        "guard_uncheck_succeeded": guard_uncheck_succeeded,
    }


def append_default_checkbox_diagnostic(path: Path | str, snapshot: Mapping[str, Any]) -> None:
    """Write/append a stage snapshot. Safe to call before owner-session teardown."""
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
