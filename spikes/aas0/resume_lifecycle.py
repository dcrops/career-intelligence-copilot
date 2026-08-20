"""SEEK résumé Default protection, disposable rotation, and cleanup policy.

Spike-only. Default detection is structural (SEEK ``Default`` badge).
Every non-Default saved résumé is a disposable tailored application CV.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

# Re-exported for SEEK row parsing (same pattern as answer_policy).
_DEFAULT_CHECKBOX = re.compile(
    r"make this my default r[eé]sum[eé]",
    re.IGNORECASE,
)

_CAPACITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"r[eé]sum[eé]\s+limit\s+reached", re.I),
    re.compile(r"please select a r[eé]sum[eé] to delete", re.I),
    re.compile(r"maximum (number of )?(saved )?(r[eé]sum[eé]s|cvs)\b", re.I),
    re.compile(r"too many (saved )?(r[eé]sum[eé]s|cvs)\b", re.I),
    re.compile(
        r"(r[eé]sum[eé]|cv) (storage|library|list) (is )?(full|at (its )?limit)",
        re.I,
    ),
    re.compile(r"you( have|'ve) reached .{0,60}(r[eé]sum[eé]|cv)", re.I),
    re.compile(r"can'?t (upload|add|save) .{0,60}(r[eé]sum[eé]|cv)", re.I),
    re.compile(r"unable to (upload|add|save) .{0,60}(r[eé]sum[eé]|cv)", re.I),
    re.compile(r"limit of \d+ (r[eé]sum[eé]s|cvs)\b", re.I),
    re.compile(r"no (more )?space .{0,40}(r[eé]sum[eé]|cv)", re.I),
)

_PDF_IN_ROW = re.compile(r"([^\n\r]+?\.pdf)", re.IGNORECASE)
_SKIP_RADIO = re.compile(
    r"(upload a cover letter|write a cover letter|"
    r"don'?t include a cover letter|do not include a cover letter|"
    r"don'?t include a r[eé]sum[eé]|do not include a r[eé]sum[eé])",
    re.IGNORECASE,
)
_COVER_LETTER_PDF = re.compile(r"cover[\s_-]*letter\.pdf$", re.IGNORECASE)

_ADDED_AGO = re.compile(
    r"added\s+(?:"
    r"less than a minute|"
    r"(?:an?|1)\s+(minute|hour|day|week|month)|"
    r"(\d+)\s+(minutes?|hours?|days?|weeks?|months?)"
    r")\s+ago",
    re.IGNORECASE,
)

_UNIT_MINUTES = {
    "minute": 1,
    "minutes": 1,
    "hour": 60,
    "hours": 60,
    "day": 1440,
    "days": 1440,
    "week": 10080,
    "weeks": 10080,
    "month": 43200,
    "months": 43200,
}


class CvRotationClass(str, Enum):
    """Lifecycle class. Filename/provenance is not used."""

    DISPOSABLE = "disposable"
    PROTECT = "protect"


class DefaultResumeChangedError(RuntimeError):
    """Account Default résumé changed unexpectedly. Do not auto-restore."""


class ResumeCapacityError(RuntimeError):
    """SEEK résumé library appears full. Do not guess a delete interaction."""


@dataclass(frozen=True)
class SeekResumeEntry:
    filename: str
    is_default: bool
    is_selected: bool
    index: int
    added_ago_minutes: int | None = None

    def to_metrics_dict(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "is_default": self.is_default,
            "is_selected": self.is_selected,
            "index": self.index,
            "added_ago_minutes": self.added_ago_minutes,
            "lifecycle": (
                CvRotationClass.PROTECT.value
                if self.is_default
                else CvRotationClass.DISPOSABLE.value
            ),
        }


@dataclass(frozen=True)
class SeekResumeSnapshot:
    entries: tuple[SeekResumeEntry, ...]
    default_filename: str | None
    default_observable: bool
    selected_filename: str | None
    ambiguous_default: bool = False

    def to_metrics_dict(self) -> dict[str, object]:
        return {
            "default_filename": self.default_filename,
            "default_observable": self.default_observable,
            "selected_filename": self.selected_filename,
            "ambiguous_default": self.ambiguous_default,
            "entries": [entry.to_metrics_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class DefaultChangeResult:
    changed: bool
    should_stop: bool
    reason: str
    before: str | None
    after: str | None


@dataclass(frozen=True)
class DefaultCheckboxOutcome:
    """Result of the post-upload Default-checkbox attempt. Never implies restore."""

    present: bool
    was_checked: bool
    still_checked: bool
    uncheck_attempted: bool
    uncheck_succeeded: bool
    should_stop: bool
    reason: str
    uncheck_returned: bool = False
    uncheck_threw: bool = False
    uncheck_exception_type: str | None = None
    uncheck_exception_message: str | None = None
    baseline_default_filename: str | None = None
    settled_default_filename: str | None = None
    checkbox_enabled: bool | None = None
    settle_poll_count: int = 0
    settle_wait_ms: int = 0


CHECKBOX_SETTLE_TIMEOUT_MS = 15_000
CHECKBOX_SETTLE_POLL_MS = 400


@dataclass(frozen=True)
class CheckboxSettleDecision:
    """One poll of post-uncheck checkbox + structural Default settling."""

    action: str
    reason: str
    checked: bool
    enabled: bool | None
    structural_default: str | None
    default_observable: bool


@dataclass(frozen=True)
class CleanupCandidate:
    filename: str | None
    index: int | None
    reason: str
    selected: bool


def classify_seek_cv_for_rotation(
    filename: str = "",
    *,
    is_default: bool = False,
) -> CvRotationClass:
    """Default badge protects; every other saved résumé is disposable.

    ``filename`` is evidence only and never decides deletability.
    """
    del filename
    if is_default:
        return CvRotationClass.PROTECT
    return CvRotationClass.DISPOSABLE


def parse_seek_added_ago_minutes(row_text: str) -> int | None:
    """Parse SEEK ``Added … ago`` into approximate minutes, or None."""
    match = _ADDED_AGO.search(row_text or "")
    if not match:
        return None
    token = match.group(0).lower()
    if "less than a minute" in token:
        return 0
    if match.group(2):
        count = int(match.group(2))
        unit = match.group(3).lower()
        return count * _UNIT_MINUTES[unit]
    unit = (match.group(1) or "").lower()
    if unit:
        return _UNIT_MINUTES[unit]
    return None


def may_auto_delete_seek_cv(filename: str = "", *, is_default: bool = False) -> bool:
    """True for every non-Default saved résumé."""
    del filename
    return not is_default


def row_is_structurally_default(row_text: str) -> bool:
    """SEEK Default badge after stripping the 'Make this my default' checkbox copy."""
    stripped = _DEFAULT_CHECKBOX.sub("", row_text or "")
    return bool(re.search(r"\bDefault\b", stripped))


def extract_pdf_filename(row_text: str) -> str | None:
    match = _PDF_IN_ROW.search(row_text or "")
    if not match:
        return None
    name = match.group(1).strip()
    name = re.sub(r"^Default\s+", "", name, flags=re.I).strip()
    name = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return name or None


def _pdf_mention_count(text: str) -> int:
    return len(re.findall(r"\.pdf\b", text or "", flags=re.IGNORECASE))


def select_resume_row_text(ancestor_texts: Sequence[str]) -> str:
    """Pick the résumé *row* from inner-to-outer ancestor innerText.

    Live SEEK (20260819T042502Z): the Default badge sits in the row container,
    not on the radio's narrow label. Use the outermost ancestor that still
    contains exactly one ``.pdf`` so the badge is included without swallowing
    the whole résumé list.
    """
    chosen = ""
    for text in ancestor_texts:
        blob = (text or "").strip()
        if not blob:
            continue
        count = _pdf_mention_count(blob)
        if count == 0:
            continue
        if count > 1:
            break
        if extract_pdf_filename(blob):
            chosen = blob
    return chosen


def looks_like_cover_letter_pdf_filename(filename: str | None) -> bool:
    """True for cover-letter PDFs, which are not saved-résumé inventory rows."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name:
        return False
    return bool(_COVER_LETTER_PDF.search(name))


def should_skip_resume_radio_row(row_text: str) -> bool:
    """Exclude cover-letter controls/files and non-résumé radios from inventory."""
    text = row_text or ""
    filename = extract_pdf_filename(text)
    if looks_like_cover_letter_pdf_filename(filename):
        return True
    if _SKIP_RADIO.search(text):
        return True
    return False


def build_seek_resume_snapshot(
    rows: Sequence[tuple[str, bool]],
) -> SeekResumeSnapshot:
    """Build a snapshot from ``(row_text, is_selected)`` radio rows."""
    entries: list[SeekResumeEntry] = []
    for index, (text, selected) in enumerate(rows):
        if should_skip_resume_radio_row(text):
            continue
        filename = extract_pdf_filename(text)
        if not filename:
            continue
        entries.append(
            SeekResumeEntry(
                filename=filename,
                is_default=row_is_structurally_default(text),
                is_selected=bool(selected),
                index=index,
                added_ago_minutes=parse_seek_added_ago_minutes(text),
            )
        )

    defaults = [entry.filename for entry in entries if entry.is_default]
    unique_defaults = list(dict.fromkeys(defaults))
    ambiguous = len(unique_defaults) > 1
    default_filename = unique_defaults[0] if len(unique_defaults) == 1 else None
    selected = next((entry.filename for entry in entries if entry.is_selected), None)
    return SeekResumeSnapshot(
        entries=tuple(entries),
        default_filename=default_filename,
        default_observable=default_filename is not None and not ambiguous,
        selected_filename=selected,
        ambiguous_default=ambiguous,
    )


def evaluate_default_change(
    before: SeekResumeSnapshot,
    after: SeekResumeSnapshot,
) -> DefaultChangeResult:
    """OBSERVE → VERIFY. Unchecking the Default checkbox is not assumed to restore.

    Stop when the structurally identified Default filename changed, became
    ambiguous, or could not be re-observed after a successful pre-upload
    observation. If Default was not observable before upload, we cannot claim
    a change and do not stop solely for that.
    """
    if before.ambiguous_default:
        return DefaultChangeResult(
            changed=True,
            should_stop=True,
            reason="pre_upload_default_ambiguous",
            before=before.default_filename,
            after=after.default_filename,
        )
    if after.ambiguous_default:
        return DefaultChangeResult(
            changed=True,
            should_stop=True,
            reason="post_upload_default_ambiguous",
            before=before.default_filename,
            after=after.default_filename,
        )
    if not before.default_observable or not before.default_filename:
        return DefaultChangeResult(
            changed=False,
            should_stop=False,
            reason="pre_upload_default_not_observable",
            before=None,
            after=after.default_filename,
        )
    if not after.default_observable or not after.default_filename:
        return DefaultChangeResult(
            changed=True,
            should_stop=True,
            reason="post_upload_default_not_observable",
            before=before.default_filename,
            after=None,
        )
    if before.default_filename.casefold() != after.default_filename.casefold():
        return DefaultChangeResult(
            changed=True,
            should_stop=True,
            reason="default_filename_changed",
            before=before.default_filename,
            after=after.default_filename,
        )
    return DefaultChangeResult(
        changed=False,
        should_stop=False,
        reason="default_unchanged",
        before=before.default_filename,
        after=after.default_filename,
    )


def application_cv_is_structural_default(
    *,
    default_filename: str | None,
    expected_filename: str,
) -> bool:
    """True when the application CV is also the account Default badge.

    Automation must not Continue in that state and must not restore Default
    by selecting another résumé.
    """
    expected = (expected_filename or "").strip()
    current = (default_filename or "").strip()
    if not expected or not current:
        return False
    return current.casefold() == expected.casefold()


def evaluate_default_checkbox_guard(
    *,
    present: bool,
    was_checked: bool,
    still_checked: bool,
    uncheck_attempted: bool,
) -> DefaultCheckboxOutcome:
    """Stop if SEEK left Make-this-my-default checked after an uncheck attempt.

    Independent of Default-badge observability. A successful uncheck still
    does not imply the previous account Default was restored.
    """
    if not present:
        return DefaultCheckboxOutcome(
            present=False,
            was_checked=False,
            still_checked=False,
            uncheck_attempted=False,
            uncheck_succeeded=False,
            should_stop=False,
            reason="checkbox_absent",
        )
    if not was_checked:
        return DefaultCheckboxOutcome(
            present=True,
            was_checked=False,
            still_checked=False,
            uncheck_attempted=False,
            uncheck_succeeded=False,
            should_stop=False,
            reason="checkbox_already_unchecked",
        )
    if uncheck_attempted and not still_checked:
        return DefaultCheckboxOutcome(
            present=True,
            was_checked=True,
            still_checked=False,
            uncheck_attempted=True,
            uncheck_succeeded=True,
            should_stop=False,
            reason="checkbox_unchecked",
        )
    return DefaultCheckboxOutcome(
        present=True,
        was_checked=True,
        still_checked=True,
        uncheck_attempted=uncheck_attempted,
        uncheck_succeeded=False,
        should_stop=True,
        reason="default_checkbox_remained_checked",
    )


def _resume_filenames_match(left: str | None, right: str | None) -> bool:
    a = (left or "").strip()
    b = (right or "").strip()
    if not a or not b:
        return False
    return a.casefold() == b.casefold()


def committed_structural_default_checkbox_locked(
    *,
    checked: bool,
    enabled: bool | None,
    selected_filename: str | None,
    default_filename: str | None,
) -> bool:
    """True when SEEK has locked Make-default on the already-Default selected résumé.

    Discriminator versus new-upload auto-default (Hatch): that state is
    checked **and enabled**. Disabled is required. ``selected == Default``
    is required. Unknown ``enabled`` is not treated as locked.
    """
    if not checked:
        return False
    if enabled is not False:
        return False
    return _resume_filenames_match(selected_filename, default_filename)


def locked_structural_default_checkbox_outcome(
    *,
    default_filename: str | None,
    selected_filename: str | None,
) -> DefaultCheckboxOutcome:
    """STOP outcome for a committed Default. Uncheck is not attempted."""
    del selected_filename
    return DefaultCheckboxOutcome(
        present=True,
        was_checked=True,
        still_checked=True,
        uncheck_attempted=False,
        uncheck_succeeded=False,
        should_stop=True,
        reason="structural_default_checkbox_locked",
        baseline_default_filename=default_filename,
        settled_default_filename=default_filename,
        checkbox_enabled=False,
        settle_poll_count=0,
        settle_wait_ms=0,
    )


def classify_checkbox_settle_tick(
    *,
    checked: bool,
    enabled: bool | None,
    current_default: str | None,
    default_observable: bool,
    baseline_default: str | None,
    baseline_observable: bool,
    application_filename: str | None,
    elapsed_ms: int,
    timeout_ms: int = CHECKBOX_SETTLE_TIMEOUT_MS,
) -> CheckboxSettleDecision:
    """Decide one post-uncheck poll. ``enabled`` is evidence only.

    Success requires the checkbox unchecked and, when a pre-upload Default was
    observable, that same structural Default filename restored. A temporary
    Default on the current application CV is expected while SEEK settles.
    """
    unexpected_third = (
        baseline_observable
        and default_observable
        and bool((current_default or "").strip())
        and not _resume_filenames_match(current_default, baseline_default)
        and not _resume_filenames_match(current_default, application_filename)
    )
    if unexpected_third:
        return CheckboxSettleDecision(
            action="stop",
            reason="default_changed_unexpectedly",
            checked=checked,
            enabled=enabled,
            structural_default=current_default,
            default_observable=default_observable,
        )
    restored = (
        baseline_observable
        and default_observable
        and _resume_filenames_match(current_default, baseline_default)
    )
    if not checked and restored:
        return CheckboxSettleDecision(
            action="success",
            reason="checkbox_unchecked",
            checked=False,
            enabled=enabled,
            structural_default=current_default,
            default_observable=True,
        )
    if not checked and not baseline_observable:
        return CheckboxSettleDecision(
            action="success",
            reason="checkbox_unchecked",
            checked=False,
            enabled=enabled,
            structural_default=current_default,
            default_observable=default_observable,
        )
    if elapsed_ms >= timeout_ms:
        if baseline_observable and not default_observable:
            reason = "default_unobservable_after_uncheck"
        else:
            reason = "default_checkbox_settle_timeout"
        return CheckboxSettleDecision(
            action="stop",
            reason=reason,
            checked=checked,
            enabled=enabled,
            structural_default=current_default,
            default_observable=default_observable,
        )
    return CheckboxSettleDecision(
        action="keep_waiting",
        reason="checkbox_settle_pending",
        checked=checked,
        enabled=enabled,
        structural_default=current_default,
        default_observable=default_observable,
    )


def checkbox_outcome_from_settle(
    *,
    was_checked: bool,
    uncheck_attempted: bool,
    tick: CheckboxSettleDecision,
    uncheck_returned: bool = False,
    uncheck_threw: bool = False,
    uncheck_exception_type: str | None = None,
    uncheck_exception_message: str | None = None,
    baseline_default: str | None = None,
    poll_count: int = 0,
    elapsed_ms: int = 0,
) -> DefaultCheckboxOutcome:
    """Map a terminal settle tick to the Default-checkbox outcome. Never restores."""
    success = tick.action == "success"
    return DefaultCheckboxOutcome(
        present=True,
        was_checked=was_checked,
        still_checked=tick.checked,
        uncheck_attempted=uncheck_attempted,
        uncheck_succeeded=success,
        should_stop=tick.action == "stop",
        reason=tick.reason,
        uncheck_returned=uncheck_returned,
        uncheck_threw=uncheck_threw,
        uncheck_exception_type=uncheck_exception_type,
        uncheck_exception_message=uncheck_exception_message,
        baseline_default_filename=baseline_default,
        settled_default_filename=tick.structural_default,
        checkbox_enabled=tick.enabled,
        settle_poll_count=poll_count,
        settle_wait_ms=elapsed_ms,
    )


def select_cleanup_candidate(entries: Sequence[SeekResumeEntry]) -> CleanupCandidate:
    """Pick the oldest non-Default résumé row.

    Prefer parsed ``Added … ago`` only when every eligible row has it.
    Otherwise treat the SEEK list as newest-first and take the last eligible
    non-Default row. Incomplete/mixed age metadata does not block rotation.
    """
    eligible = [
        entry
        for entry in entries
        if not entry.is_default
        and not looks_like_cover_letter_pdf_filename(entry.filename)
    ]
    if not eligible:
        return CleanupCandidate(
            filename=None,
            index=None,
            reason="no_non_default_resume",
            selected=False,
        )
    ages = [entry.added_ago_minutes for entry in eligible]
    if ages and all(age is not None for age in ages):
        oldest_minutes = max(age for age in ages if age is not None)
        same_age = [
            entry for entry in eligible if entry.added_ago_minutes == oldest_minutes
        ]
        chosen = same_age[-1]
        return CleanupCandidate(
            filename=chosen.filename,
            index=chosen.index,
            reason="oldest_non_default_by_added_age",
            selected=True,
        )
    chosen = eligible[-1]
    return CleanupCandidate(
        filename=chosen.filename,
        index=chosen.index,
        reason="oldest_non_default_last_in_newest_first_list",
        selected=True,
    )


def detect_resume_capacity_message(body_text: str) -> str | None:
    """Return a matched capacity phrase, or None if not clearly a full library."""
    text = body_text or ""
    for pattern in _CAPACITY_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return None
