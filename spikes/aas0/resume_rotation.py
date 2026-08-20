"""Bounded SEEK résumé rotation policy (AAS-0.1).

Protected: structural Default only. Disposable: every other saved résumé.
Overflow menu (owner observation): **Download** and **Delete**. Confirmation
(live ``20260819T091149Z``): ``Are you sure you want to delete this document?``
plus the candidate filename, with **Delete**, **Cancel**, and Dismiss/Close.
Only the dialog Delete may be clicked. Confirmation action names are
normalised (Unicode format characters such as U+2060 stripped) before
comparison.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Protocol, Sequence

from .resume_lifecycle import (
    CleanupCandidate,
    SeekResumeEntry,
    SeekResumeSnapshot,
    evaluate_default_change,
    select_cleanup_candidate,
)

# Owner-observed overflow actions on a saved-résumé kebab (19 Aug 2026).
SEEK_RESUME_DELETE_ACTION = "Delete"
SEEK_RESUME_DOWNLOAD_ACTION = "Download"
SEEK_RESUME_DELETE_MENU_LABELS: tuple[str, ...] = (SEEK_RESUME_DELETE_ACTION,)
SEEK_RESUME_OVERFLOW_MENU_ACTIONS: tuple[str, ...] = (
    SEEK_RESUME_DOWNLOAD_ACTION,
    SEEK_RESUME_DELETE_ACTION,
)
SEEK_RESUME_DELETE_CONFIRMATION_PROMPT = (
    "Are you sure you want to delete this document?"
)
SEEK_RESUME_DELETE_CONFIRMATION_CANCEL = "Cancel"
SEEK_RESUME_DELETE_CONFIRMATION_CLOSE = "Close"
SEEK_RESUME_DELETE_CONFIRMATION_DISMISS = "Dismiss"
SEEK_RESUME_DELETE_CONFIRMATION_ALLOWED_NON_DELETE: frozenset[str] = frozenset(
    {
        SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
        SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
        SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
    }
)
_PDF_IN_TEXT = re.compile(r"([^\n\r]+?\.pdf)", re.IGNORECASE)


def normalise_confirmation_action_name(name: str | None) -> str:
    """Strip Unicode format characters (e.g. U+2060) and surrounding whitespace."""
    without_format = "".join(
        char for char in (name or "") if unicodedata.category(char) != "Cf"
    )
    return without_format.strip()


def confirmation_accessible_name(
    *,
    aria_label: str | None = None,
    inner_text: str | None = None,
) -> str:
    """Prefer accessible name; do not identify Delete by inner_text when labelled."""
    labelled = (aria_label or "").strip()
    if labelled:
        return labelled
    return (inner_text or "").strip()


ROTATION_TRIGGER_REASONS = frozenset(
    {
        "expected_cv_not_present",
        "resume_upload_spinner_timeout",
        "resume_upload_still_processing",
        "resume_capacity_blocked",
    }
)

# Match CV-selection wait: poll, do not one-shot sleep.
DELETION_VERIFICATION_TIMEOUT_MS = 15_000
DELETION_VERIFICATION_POLL_MS = 400


@dataclass(frozen=True)
class CleanupSkip:
    filename: str
    index: int
    reason: str


@dataclass(frozen=True)
class RotationTrigger:
    should_attempt: bool
    reason: str


@dataclass(frozen=True)
class DeletionVerification:
    should_stop: bool
    reason: str
    deleted_filename: str | None
    default_before: str | None
    default_after: str | None


@dataclass(frozen=True)
class DeletionWaitDecision:
    """One bounded post-delete inventory poll."""

    action: Literal["verified", "keep_waiting", "stop"]
    reason: str
    poll_count: int
    elapsed_ms: int
    snapshot: SeekResumeSnapshot
    verification: DeletionVerification


@dataclass(frozen=True)
class RotationDecision:
    """One-delete / one-retry policy outcome."""

    action: Literal["continue", "attempt_delete", "retry_upload_once", "stop"]
    reason: str
    candidate: CleanupCandidate
    skips: tuple[CleanupSkip, ...]
    deletion_verified: bool
    retry_attempted: bool


@dataclass(frozen=True)
class ResumeRowMenu:
    """One résumé row's overflow controls, identified by list index."""

    filename: str
    index: int
    is_default: bool
    overflow_control_count: int
    menu_open: bool
    menu_actions: tuple[str, ...]


@dataclass(frozen=True)
class DeleteClickPlan:
    action: Literal["open_overflow", "click_delete", "stop"]
    reason: str
    target_filename: str | None
    target_index: int | None
    menu_action: str | None


@dataclass(frozen=True)
class DeleteConfirmationObservation:
    """Visible confirmation dialog after the row-scoped menu Delete."""

    dialog_count: int
    prompt_present: bool
    dialog_text: str
    mentions_candidate: bool
    other_pdf_filenames: tuple[str, ...]
    delete_action_count: int
    cancel_action_count: int
    extra_action_names: tuple[str, ...]
    action_names_raw: tuple[str, ...] = ()
    action_names_normalised: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeleteConfirmationPlan:
    action: Literal["click_confirm_delete", "stop"]
    reason: str


class ResumeDeleteDriver(Protocol):
    """Row-scoped delete. Tests use a fake; live uses Playwright."""

    def row_menus(self) -> Sequence[ResumeRowMenu]: ...

    def confirmation_dialog_visible(self) -> bool: ...

    def observe_delete_confirmation(
        self, candidate_filename: str | None = None
    ) -> DeleteConfirmationObservation: ...

    def open_overflow(self, row_index: int) -> str: ...

    def click_exact_delete(self) -> str: ...

    def click_confirmation_delete(self) -> str: ...


def explain_cleanup_skips(entries: Sequence[SeekResumeEntry]) -> tuple[CleanupSkip, ...]:
    """Only the structural Default is ineligible for automatic deletion."""
    skips: list[CleanupSkip] = []
    for entry in entries:
        if entry.is_default:
            skips.append(
                CleanupSkip(
                    filename=entry.filename,
                    index=entry.index,
                    reason="structurally_default",
                )
            )
    return tuple(skips)


def evaluate_rotation_trigger(
    *,
    upload_failure_reason: str,
    rotation_already_attempted: bool,
    expected_cv_present: bool = False,
) -> RotationTrigger:
    """Rotate only after concrete upload failure, and at most once per run.

    A full library must not rotate when the exact expected CV is already saved.
    """
    if expected_cv_present:
        return RotationTrigger(
            should_attempt=False,
            reason="expected_cv_already_present_no_rotation",
        )
    reason = (upload_failure_reason or "").strip()
    if rotation_already_attempted:
        return RotationTrigger(should_attempt=False, reason="rotation_already_attempted")
    if reason in ROTATION_TRIGGER_REASONS:
        return RotationTrigger(should_attempt=True, reason=reason)
    return RotationTrigger(should_attempt=False, reason="no_upload_failure_trigger")


def seek_delete_menu_is_observed() -> bool:
    """True only when preserved evidence named the delete/remove control."""
    return bool(SEEK_RESUME_DELETE_MENU_LABELS)


def evaluate_deletion_verification(
    *,
    before: SeekResumeSnapshot,
    after: SeekResumeSnapshot,
    deleted_filename: str,
    deleted_index: int | None = None,
) -> DeletionVerification:
    """Confirm exactly one intended row left and Default did not move."""
    target = (deleted_filename or "").strip()
    default_before = before.default_filename
    default_after = after.default_filename
    if deleted_index is None and not target:
        return DeletionVerification(
            should_stop=True,
            reason="deleted_filename_missing",
            deleted_filename=None,
            default_before=default_before,
            default_after=default_after,
        )
    if deleted_index is not None:
        intended = next(
            (entry for entry in before.entries if entry.index == deleted_index),
            None,
        )
        if intended is None:
            return DeletionVerification(
                should_stop=True,
                reason="deleted_filename_was_not_in_inventory",
                deleted_filename=target or None,
                default_before=default_before,
                default_after=default_after,
            )
        target = intended.filename
        if len(after.entries) != len(before.entries) - 1:
            return DeletionVerification(
                should_stop=True,
                reason="deleted_filename_still_present"
                if len(after.entries) >= len(before.entries)
                else "deleted_filename_count_unexpected",
                deleted_filename=target,
                default_before=default_before,
                default_after=default_after,
            )
        remaining = [
            entry for entry in before.entries if entry.index != deleted_index
        ]
        expected = [entry.filename.casefold() for entry in remaining]
        observed = [entry.filename.casefold() for entry in after.entries]
        if expected != observed:
            return DeletionVerification(
                should_stop=True,
                reason="wrong_row_disappeared",
                deleted_filename=target,
                default_before=default_before,
                default_after=default_after,
            )
    else:
        before_counts = Counter(entry.filename for entry in before.entries)
        after_counts = Counter(entry.filename for entry in after.entries)
        if before_counts[target] < 1:
            return DeletionVerification(
                should_stop=True,
                reason="deleted_filename_was_not_in_inventory",
                deleted_filename=target,
                default_before=default_before,
                default_after=default_after,
            )
        if len(after.entries) != len(before.entries) - 1:
            return DeletionVerification(
                should_stop=True,
                reason="deleted_filename_still_present"
                if len(after.entries) >= len(before.entries)
                else "deleted_filename_count_unexpected",
                deleted_filename=target,
                default_before=default_before,
                default_after=default_after,
            )
        for name, count in before_counts.items():
            if name == target:
                continue
            if after_counts[name] != count:
                return DeletionVerification(
                    should_stop=True,
                    reason="wrong_row_disappeared",
                    deleted_filename=target,
                    default_before=default_before,
                    default_after=default_after,
                )
        extras = [name for name in after_counts if name not in before_counts]
        if extras:
            return DeletionVerification(
                should_stop=True,
                reason="unexpected_resume_appeared",
                deleted_filename=target,
                default_before=default_before,
                default_after=default_after,
            )
        if after_counts[target] != before_counts[target] - 1:
            return DeletionVerification(
                should_stop=True,
                reason="deleted_filename_still_present"
                if after_counts[target] >= before_counts[target]
                else "deleted_filename_count_unexpected",
                deleted_filename=target,
                default_before=default_before,
                default_after=default_after,
            )
    default_change = evaluate_default_change(before, after)
    if default_change.should_stop:
        reason = "default_changed_after_deletion"
        if default_change.reason in {
            "post_upload_default_not_observable",
            "post_upload_default_ambiguous",
        }:
            reason = "default_unobservable_after_deletion"
        return DeletionVerification(
            should_stop=True,
            reason=reason,
            deleted_filename=target,
            default_before=default_before,
            default_after=default_after,
        )
    return DeletionVerification(
        should_stop=False,
        reason="deletion_verified",
        deleted_filename=target,
        default_before=default_before,
        default_after=default_after,
    )


def _intended_delete_filename(
    before: SeekResumeSnapshot,
    deleted_filename: str,
    deleted_index: int | None,
) -> str:
    if deleted_index is not None:
        intended = next(
            (entry for entry in before.entries if entry.index == deleted_index),
            None,
        )
        if intended is not None:
            return intended.filename
    return (deleted_filename or "").strip()


def _filename_copy_count(snapshot: SeekResumeSnapshot, filename: str) -> int:
    key = (filename or "").casefold()
    if not key:
        return 0
    return sum(1 for entry in snapshot.entries if entry.filename.casefold() == key)


def classify_deletion_wait_tick(
    *,
    before: SeekResumeSnapshot,
    after: SeekResumeSnapshot,
    verification: DeletionVerification,
    deleted_filename: str,
    deleted_index: int | None,
    elapsed_ms: int,
    timeout_ms: int,
    poll_count: int,
) -> DeletionWaitDecision:
    """Keep waiting while SEEK inventory is still settling; fail closed otherwise."""
    if verification.reason == "deletion_verified":
        return DeletionWaitDecision(
            action="verified",
            reason="deletion_verified",
            poll_count=poll_count,
            elapsed_ms=elapsed_ms,
            snapshot=after,
            verification=verification,
        )
    default_before = (before.default_filename or "").strip()
    default_after = (after.default_filename or "").strip()
    if (
        default_before
        and default_after
        and default_after.casefold() != default_before.casefold()
    ):
        return DeletionWaitDecision(
            action="stop",
            reason="default_changed_after_deletion",
            poll_count=poll_count,
            elapsed_ms=elapsed_ms,
            snapshot=after,
            verification=verification,
        )
    if verification.reason == "wrong_row_disappeared":
        return DeletionWaitDecision(
            action="stop",
            reason="wrong_row_disappeared",
            poll_count=poll_count,
            elapsed_ms=elapsed_ms,
            snapshot=after,
            verification=verification,
        )
    if verification.reason in {
        "deleted_filename_missing",
        "deleted_filename_was_not_in_inventory",
    }:
        return DeletionWaitDecision(
            action="stop",
            reason=verification.reason,
            poll_count=poll_count,
            elapsed_ms=elapsed_ms,
            snapshot=after,
            verification=verification,
        )
    intended = _intended_delete_filename(before, deleted_filename, deleted_index)
    still_present = _filename_copy_count(after, intended) >= _filename_copy_count(
        before, intended
    )
    if (
        verification.reason == "default_unobservable_after_deletion"
        and not still_present
    ):
        return DeletionWaitDecision(
            action="stop",
            reason="default_unobservable_after_deletion",
            poll_count=poll_count,
            elapsed_ms=elapsed_ms,
            snapshot=after,
            verification=verification,
        )
    if elapsed_ms >= timeout_ms:
        return DeletionWaitDecision(
            action="stop",
            reason="resume_delete_verification_timeout",
            poll_count=poll_count,
            elapsed_ms=elapsed_ms,
            snapshot=after,
            verification=verification,
        )
    return DeletionWaitDecision(
        action="keep_waiting",
        reason=verification.reason or "deleted_filename_still_present",
        poll_count=poll_count,
        elapsed_ms=elapsed_ms,
        snapshot=after,
        verification=verification,
    )


def wait_until_deletion_verified(
    observe: Callable[[], SeekResumeSnapshot],
    *,
    before: SeekResumeSnapshot,
    deleted_filename: str,
    deleted_index: int | None,
    timeout_ms: int = DELETION_VERIFICATION_TIMEOUT_MS,
    poll_ms: int = DELETION_VERIFICATION_POLL_MS,
    wait: Callable[[int], None] | None = None,
    now_ms: Callable[[], int] | None = None,
) -> DeletionWaitDecision:
    """Poll saved-résumé inventory until deletion invariants hold or timeout."""
    started = time.monotonic()
    synthetic_ms = 0

    def _now() -> int:
        if now_ms is not None:
            return now_ms()
        wall = int((time.monotonic() - started) * 1000)
        return max(wall, synthetic_ms)

    poll_count = 0
    while True:
        after = observe()
        poll_count += 1
        verification = evaluate_deletion_verification(
            before=before,
            after=after,
            deleted_filename=deleted_filename,
            deleted_index=deleted_index,
        )
        tick = classify_deletion_wait_tick(
            before=before,
            after=after,
            verification=verification,
            deleted_filename=deleted_filename,
            deleted_index=deleted_index,
            elapsed_ms=_now(),
            timeout_ms=timeout_ms,
            poll_count=poll_count,
        )
        if tick.action != "keep_waiting":
            return tick
        if wait is not None:
            wait(poll_ms)
        synthetic_ms += poll_ms


def evaluate_rotation_decision(
    *,
    entries: Sequence[SeekResumeEntry],
    upload_failure_reason: str,
    rotation_already_attempted: bool,
    menu_observed: bool | None = None,
    deletion_verified: bool = False,
    retry_attempted: bool = False,
    retry_expected_cv_selected: bool = False,
    default_observable_before: bool = True,
    expected_cv_present: bool = False,
) -> RotationDecision:
    """Bounded recovery: at most one legal delete, then one verified retry."""
    skips = explain_cleanup_skips(entries)
    candidate = select_cleanup_candidate(entries)
    trigger = evaluate_rotation_trigger(
        upload_failure_reason=upload_failure_reason,
        rotation_already_attempted=rotation_already_attempted,
        expected_cv_present=expected_cv_present,
    )
    observed = seek_delete_menu_is_observed() if menu_observed is None else menu_observed

    if rotation_already_attempted:
        if retry_attempted and retry_expected_cv_selected:
            return RotationDecision(
                action="continue",
                reason="retry_expected_cv_selected",
                candidate=candidate,
                skips=skips,
                deletion_verified=deletion_verified,
                retry_attempted=True,
            )
        return RotationDecision(
            action="stop",
            reason="retry_failed_no_second_deletion"
            if retry_attempted
            else "rotation_already_attempted",
            candidate=candidate,
            skips=skips,
            deletion_verified=deletion_verified,
            retry_attempted=retry_attempted,
        )
    if not trigger.should_attempt:
        return RotationDecision(
            action="stop",
            reason=trigger.reason,
            candidate=candidate,
            skips=skips,
            deletion_verified=False,
            retry_attempted=False,
        )
    if not candidate.selected:
        return RotationDecision(
            action="stop",
            reason=candidate.reason or "no_safe_deletion_candidate",
            candidate=candidate,
            skips=skips,
            deletion_verified=False,
            retry_attempted=False,
        )
    if not default_observable_before:
        return RotationDecision(
            action="stop",
            reason="default_not_observable_before_deletion",
            candidate=candidate,
            skips=skips,
            deletion_verified=False,
            retry_attempted=False,
        )
    if not observed:
        return RotationDecision(
            action="stop",
            reason="seek_delete_menu_unobserved",
            candidate=candidate,
            skips=skips,
            deletion_verified=False,
            retry_attempted=False,
        )
    if not deletion_verified:
        return RotationDecision(
            action="attempt_delete",
            reason="attempt_observed_delete",
            candidate=candidate,
            skips=skips,
            deletion_verified=False,
            retry_attempted=False,
        )
    if not retry_attempted:
        return RotationDecision(
            action="retry_upload_once",
            reason="deletion_verified_retry_once",
            candidate=candidate,
            skips=skips,
            deletion_verified=True,
            retry_attempted=False,
        )
    if retry_expected_cv_selected:
        return RotationDecision(
            action="continue",
            reason="retry_expected_cv_selected",
            candidate=candidate,
            skips=skips,
            deletion_verified=True,
            retry_attempted=True,
        )
    return RotationDecision(
        action="stop",
        reason="retry_failed_no_second_deletion",
        candidate=candidate,
        skips=skips,
        deletion_verified=True,
        retry_attempted=True,
    )


def refuse_unobserved_resume_deletion(
    candidate_filename: str | None,
    *,
    candidate_index: int | None = None,
) -> str:
    """Refuse when Delete is not an observed menu label."""
    if not (candidate_filename or "").strip() and candidate_index is None:
        return "no_candidate"
    if not seek_delete_menu_is_observed():
        return "refused_unobserved"
    return "menu_observed"


def plan_resume_delete_click(
    *,
    candidate_filename: str | None = None,
    candidate_index: int | None = None,
    rows: Sequence[ResumeRowMenu],
    confirmation_dialog_visible: bool = False,
) -> DeleteClickPlan:
    """Bind overflow+Delete to the candidate row index. Filename may be duplicated."""
    if candidate_index is None:
        return DeleteClickPlan("stop", "no_candidate", candidate_filename, None, None)
    if confirmation_dialog_visible:
        return DeleteClickPlan(
            "stop",
            "resume_delete_confirmation_unobserved",
            candidate_filename,
            candidate_index,
            None,
        )
    matches = [row for row in rows if row.index == candidate_index]
    if not matches:
        return DeleteClickPlan(
            "stop", "row_not_found", candidate_filename, candidate_index, None
        )
    if len(matches) != 1:
        return DeleteClickPlan(
            "stop",
            "row_association_ambiguous",
            candidate_filename,
            candidate_index,
            None,
        )
    row = matches[0]
    if row.is_default:
        return DeleteClickPlan(
            "stop", "default_row_protected", row.filename, candidate_index, None
        )
    if row.overflow_control_count < 1:
        return DeleteClickPlan(
            "stop", "overflow_not_found_on_row", row.filename, candidate_index, None
        )
    if row.overflow_control_count != 1:
        return DeleteClickPlan(
            "stop", "overflow_ambiguous_on_row", row.filename, candidate_index, None
        )
    open_menus = [item for item in rows if item.menu_open]
    if not row.menu_open:
        if open_menus:
            return DeleteClickPlan(
                "stop", "other_resume_menu_open", row.filename, candidate_index, None
            )
        return DeleteClickPlan(
            "open_overflow",
            "open_candidate_overflow",
            row.filename,
            candidate_index,
            None,
        )
    if len(open_menus) != 1 or open_menus[0].index != candidate_index:
        return DeleteClickPlan(
            "stop",
            "menu_association_ambiguous"
            if len(open_menus) != 1
            else "other_resume_menu_open",
            row.filename,
            candidate_index,
            None,
        )
    if SEEK_RESUME_DELETE_ACTION not in row.menu_actions:
        return DeleteClickPlan(
            "stop", "delete_action_not_visible", row.filename, candidate_index, None
        )
    if row.menu_actions.count(SEEK_RESUME_DELETE_ACTION) != 1:
        return DeleteClickPlan(
            "stop", "menu_association_ambiguous", row.filename, candidate_index, None
        )
    return DeleteClickPlan(
        "click_delete",
        "click_exact_delete",
        row.filename,
        candidate_index,
        SEEK_RESUME_DELETE_ACTION,
    )


def _normalise_dialog_filename(filename: str | None) -> str:
    return (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()


def pdf_filenames_in_dialog_text(dialog_text: str) -> tuple[str, ...]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _PDF_IN_TEXT.finditer(dialog_text or ""):
        name = _normalise_dialog_filename(match.group(1))
        key = name.casefold()
        if name and key not in seen:
            seen.add(key)
            found.append(name)
    return tuple(found)


def dialog_mentions_candidate_filename(dialog_text: str, candidate_filename: str | None) -> bool:
    expected = _normalise_dialog_filename(candidate_filename)
    if not expected:
        return False
    return expected.casefold() in (dialog_text or "").casefold()


def empty_delete_confirmation_observation() -> DeleteConfirmationObservation:
    return DeleteConfirmationObservation(
        dialog_count=0,
        prompt_present=False,
        dialog_text="",
        mentions_candidate=False,
        other_pdf_filenames=(),
        delete_action_count=0,
        cancel_action_count=0,
        extra_action_names=(),
        action_names_raw=(),
        action_names_normalised=(),
    )


def build_delete_confirmation_observation(
    *,
    dialog_count: int,
    dialog_text: str,
    candidate_filename: str | None,
    action_names: Sequence[str],
) -> DeleteConfirmationObservation:
    text = dialog_text or ""
    expected = _normalise_dialog_filename(candidate_filename)
    pdfs = pdf_filenames_in_dialog_text(text)
    others = tuple(
        name
        for name in pdfs
        if expected and name.casefold() != expected.casefold()
    )
    raw = tuple((name or "") for name in action_names if (name or "").strip())
    names = tuple(
        normalised
        for normalised in (normalise_confirmation_action_name(name) for name in raw)
        if normalised
    )
    allowed_non_delete = SEEK_RESUME_DELETE_CONFIRMATION_ALLOWED_NON_DELETE
    extra = tuple(
        name
        for name in names
        if name != SEEK_RESUME_DELETE_ACTION and name not in allowed_non_delete
    )
    return DeleteConfirmationObservation(
        dialog_count=dialog_count,
        prompt_present=SEEK_RESUME_DELETE_CONFIRMATION_PROMPT.casefold() in text.casefold(),
        dialog_text=text,
        mentions_candidate=dialog_mentions_candidate_filename(text, candidate_filename),
        other_pdf_filenames=others,
        delete_action_count=sum(1 for name in names if name == SEEK_RESUME_DELETE_ACTION),
        cancel_action_count=sum(
            1 for name in names if name == SEEK_RESUME_DELETE_CONFIRMATION_CANCEL
        ),
        extra_action_names=extra,
        action_names_raw=raw,
        action_names_normalised=names,
    )


def plan_resume_delete_confirmation(
    *,
    candidate_filename: str | None,
    observation: DeleteConfirmationObservation,
) -> DeleteConfirmationPlan:
    """Click dialog Delete only for the exact observed SEEK confirmation UI.

    Allowed non-clicked controls: Cancel, Dismiss, and Close. Unknown named
    actions, extra dialogs, or extra Delete controls stop. Action names are
    normalised before comparison.
    """
    if observation.dialog_count == 0:
        return DeleteConfirmationPlan("stop", "resume_delete_confirmation_unobserved")
    if observation.dialog_count != 1:
        return DeleteConfirmationPlan(
            "stop", "resume_delete_confirmation_multiple_dialogs"
        )
    if not observation.prompt_present or observation.extra_action_names:
        return DeleteConfirmationPlan("stop", "resume_delete_confirmation_unobserved")
    if observation.cancel_action_count > 1:
        return DeleteConfirmationPlan("stop", "resume_delete_confirmation_unobserved")
    expected = _normalise_dialog_filename(candidate_filename)
    if not expected:
        return DeleteConfirmationPlan("stop", "no_candidate")
    if not observation.mentions_candidate:
        if observation.other_pdf_filenames:
            return DeleteConfirmationPlan(
                "stop", "resume_delete_confirmation_filename_mismatch"
            )
        return DeleteConfirmationPlan(
            "stop", "resume_delete_confirmation_filename_missing"
        )
    if observation.other_pdf_filenames:
        return DeleteConfirmationPlan(
            "stop", "resume_delete_confirmation_filename_mismatch"
        )
    if observation.delete_action_count < 1:
        return DeleteConfirmationPlan("stop", "resume_delete_confirmation_unobserved")
    if observation.delete_action_count != 1:
        return DeleteConfirmationPlan(
            "stop", "resume_delete_confirmation_multiple_delete_actions"
        )
    return DeleteConfirmationPlan("click_confirm_delete", "click_observed_confirm_delete")


def confirmation_planner_branch(
    observation: DeleteConfirmationObservation,
    candidate_filename: str | None,
) -> str:
    """Stable branch id for diagnostics. Does not change planner action/reason."""
    if observation.dialog_count == 0:
        return "dialog_count_0"
    if observation.dialog_count != 1:
        return "multiple_dialogs"
    if not observation.prompt_present:
        return "prompt_missing"
    if observation.extra_action_names:
        return "extra_actions"
    if observation.cancel_action_count > 1:
        return "cancel_count_gt_1"
    if not _normalise_dialog_filename(candidate_filename):
        return "no_candidate"
    if not observation.mentions_candidate:
        return (
            "filename_mismatch"
            if observation.other_pdf_filenames
            else "filename_missing"
        )
    if observation.other_pdf_filenames:
        return "filename_mismatch"
    if observation.delete_action_count < 1:
        return "delete_count_0"
    if observation.delete_action_count != 1:
        return "multiple_delete_actions"
    return "click_observed_confirm_delete"


def observation_diagnostic_snapshot(
    *,
    stage: str,
    candidate_filename: str | None,
    observation: DeleteConfirmationObservation,
    plan: DeleteConfirmationPlan | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize planner inputs. Extra DOM fields come from the live driver."""
    if plan is None:
        plan = plan_resume_delete_confirmation(
            candidate_filename=candidate_filename,
            observation=observation,
        )
    snapshot: dict[str, Any] = {
        "stage": stage,
        "candidate_filename": candidate_filename,
        "dialog_count": observation.dialog_count,
        "dialog_text": observation.dialog_text,
        "prompt_present": observation.prompt_present,
        "mentions_candidate": observation.mentions_candidate,
        "other_pdf_filenames": list(observation.other_pdf_filenames),
        "delete_action_count": observation.delete_action_count,
        "cancel_action_count": observation.cancel_action_count,
        "close_action_count": sum(
            1
            for name in observation.action_names_normalised
            if name == SEEK_RESUME_DELETE_CONFIRMATION_CLOSE
        ),
        "dismiss_action_count": sum(
            1
            for name in observation.action_names_normalised
            if name == SEEK_RESUME_DELETE_CONFIRMATION_DISMISS
        ),
        "extra_action_names": list(observation.extra_action_names),
        "planner_branch": confirmation_planner_branch(
            observation, candidate_filename
        ),
        "plan_action": plan.action,
        "plan_reason": plan.reason,
        "detector_roles": ["alertdialog", "dialog"],
        "dialogs": [],
        "controls": [],
        "action_names_raw": list(observation.action_names_raw),
        "action_names_normalised": list(observation.action_names_normalised),
    }
    if extra:
        snapshot.update(extra)
    return snapshot


def append_confirmation_diagnostic(path: Path | str, snapshot: dict[str, Any]) -> None:
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
    payload["snapshots"].append(snapshot)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def dump_delete_confirmation_observation(
    driver: ResumeDeleteDriver,
    *,
    path: Path | str,
    stage: str,
    candidate_filename: str | None,
    observation: DeleteConfirmationObservation | None = None,
    plan: DeleteConfirmationPlan | None = None,
) -> None:
    """Read-only dump. Never clicks. Live driver may attach DOM control details."""
    capture = getattr(driver, "capture_confirmation_diagnostic", None)
    if callable(capture):
        capture(
            path=path,
            stage=stage,
            candidate_filename=candidate_filename,
            observation=observation,
            plan=plan,
        )
        return
    if observation is None:
        observation = driver.observe_delete_confirmation(candidate_filename)
    append_confirmation_diagnostic(
        path,
        observation_diagnostic_snapshot(
            stage=stage,
            candidate_filename=candidate_filename,
            observation=observation,
            plan=plan,
        ),
    )


def perform_one_resume_deletion(
    driver: ResumeDeleteDriver,
    *,
    candidate_filename: str | None = None,
    candidate_index: int | None = None,
    diagnostic_path: Path | str | None = None,
) -> str:
    """Open the candidate kebab, click menu Delete, then the observed dialog Delete."""

    def _dump(
        stage: str,
        observation: DeleteConfirmationObservation | None = None,
        plan: DeleteConfirmationPlan | None = None,
    ) -> None:
        if diagnostic_path is None:
            return
        try:
            dump_delete_confirmation_observation(
                driver,
                path=diagnostic_path,
                stage=stage,
                candidate_filename=candidate_filename,
                observation=observation,
                plan=plan,
            )
        except Exception:  # noqa: BLE001
            return

    if candidate_index is None:
        return "no_candidate"
    _dump("pre_overflow")
    if driver.confirmation_dialog_visible():
        return "resume_delete_confirmation_unobserved"
    plan = plan_resume_delete_click(
        candidate_filename=candidate_filename,
        candidate_index=candidate_index,
        rows=driver.row_menus(),
        confirmation_dialog_visible=False,
    )
    if plan.action == "stop":
        return plan.reason
    if plan.action == "open_overflow":
        opened = driver.open_overflow(plan.target_index if plan.target_index is not None else -1)
        if opened != "opened":
            return opened
        _dump("post_overflow")
        plan = plan_resume_delete_click(
            candidate_filename=candidate_filename,
            candidate_index=candidate_index,
            rows=driver.row_menus(),
            confirmation_dialog_visible=driver.confirmation_dialog_visible(),
        )
        if plan.action == "stop":
            return plan.reason
    if plan.action != "click_delete" or plan.menu_action != SEEK_RESUME_DELETE_ACTION:
        return plan.reason
    clicked = driver.click_exact_delete()
    if clicked != "clicked":
        return clicked
    observation = driver.observe_delete_confirmation(candidate_filename)
    confirm = plan_resume_delete_confirmation(
        candidate_filename=candidate_filename,
        observation=observation,
    )
    _dump("post_menu_delete", observation=observation, plan=confirm)
    if confirm.action != "click_confirm_delete":
        return confirm.reason
    _dump("confirm_click", observation=observation, plan=confirm)
    confirmed = driver.click_confirmation_delete()
    if confirmed != "clicked":
        return confirmed
    return "clicked_delete"


def skips_as_metrics(skips: Sequence[CleanupSkip]) -> list[dict[str, object]]:
    return [
        {"filename": skip.filename, "index": skip.index, "reason": skip.reason}
        for skip in skips
    ]
