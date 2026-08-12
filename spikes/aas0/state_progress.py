"""Spike-only helpers: verify interactive actions actually change application state."""

from __future__ import annotations

import re
from dataclasses import dataclass

# SEEK Choose Documents validation observed in AAS-0 run 20260812T042513Z.
_VALIDATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"cover\s*letter\s*[-–—:]\s*please\s+make\s+a\s+selection", re.I),
    re.compile(r"please\s+make\s+a\s+selection", re.I),
    re.compile(
        r"before\s+you\s+can\s+continue\s+with\s+the\s+application",
        re.I,
    ),
)

_STEP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(choose\s+documents)\b", re.I),
    re.compile(r"\b(answer\s+employer\s+questions)\b", re.I),
    re.compile(r"\b(update\s+seek\s+profile)\b", re.I),
    re.compile(r"\b(review\s+and\s+submit)\b", re.I),
)


@dataclass(frozen=True)
class PageFingerprint:
    """Minimal snapshot used to detect whether Continue actually advanced."""

    url: str
    step_label: str
    validation_messages: tuple[str, ...]
    marker: str = ""


def detect_validation_messages(body_text: str) -> tuple[str, ...]:
    """Return known blocking validation phrases found in page text."""
    text = body_text or ""
    found: list[str] = []
    for pattern in _VALIDATION_PATTERNS:
        match = pattern.search(text)
        if match:
            phrase = match.group(0).strip()
            if phrase.lower() not in {f.lower() for f in found}:
                found.append(phrase)
    return tuple(found)


def infer_step_label(body_text: str) -> str:
    """Best-effort active step label from visible body text."""
    text = body_text or ""
    # Prefer first matching known SEEK apply step in document order.
    earliest: tuple[int, str] | None = None
    for pattern in _STEP_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        label = re.sub(r"\s+", " ", match.group(1)).strip().lower()
        if earliest is None or match.start() < earliest[0]:
            earliest = (match.start(), label)
    return earliest[1] if earliest else ""


def fingerprint_from_text(*, url: str, body_text: str, marker: str = "") -> PageFingerprint:
    return PageFingerprint(
        url=(url or "").strip(),
        step_label=infer_step_label(body_text),
        validation_messages=detect_validation_messages(body_text),
        marker=marker,
    )


def state_advanced(before: PageFingerprint, after: PageFingerprint) -> bool:
    """True when post-condition evidence shows the application moved forward.

    A successful Continue must not be inferred from the click alone.
    Presence of validation messages on ``after`` means the step FAILED.
    """
    if after.validation_messages:
        return False
    if before.url and after.url and before.url != after.url:
        return True
    if before.step_label and after.step_label and before.step_label != after.step_label:
        return True
    if before.marker and after.marker and before.marker != after.marker:
        return True
    return False


class SameStateRetryGuard:
    """Bound retries when Continue does not change application state."""

    def __init__(self, *, max_failures: int = 2) -> None:
        if max_failures < 1:
            raise ValueError("max_failures must be >= 1")
        self.max_failures = max_failures
        self.failures = 0
        self.last_fingerprint: PageFingerprint | None = None

    def record(self, before: PageFingerprint, after: PageFingerprint) -> str:
        """Return ``advanced``, ``retry``, or ``stop``."""
        if state_advanced(before, after):
            self.failures = 0
            self.last_fingerprint = after
            return "advanced"
        self.failures += 1
        self.last_fingerprint = after
        if self.failures >= self.max_failures:
            return "stop"
        return "retry"


class CoverLetterGateError(RuntimeError):
    """Raised when cover-letter preconditions for upload/Continue are not met."""


def assert_cover_letter_radio_checked(checked: bool) -> None:
    if not checked:
        raise CoverLetterGateError(
            "Cover-letter method radio is not checked; "
            "refusing upload and Continue."
        )


def assert_may_continue_documents_step(
    *,
    radio_checked: bool,
    validation_messages: tuple[str, ...] | list[str],
) -> None:
    assert_cover_letter_radio_checked(radio_checked)
    if validation_messages:
        joined = "; ".join(validation_messages)
        raise CoverLetterGateError(
            f"SEEK validation blocks progress: {joined}"
        )
