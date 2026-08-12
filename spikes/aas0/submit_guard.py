"""Final-submission guard for AAS-0.

Distinguishes application-entry / navigation controls from irreversible
final-submission controls. Prefer page-state signals over label matching alone.
When classification is ambiguous, refuse activation and require owner decision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ControlClass(str, Enum):
    """Whether a control may be activated during the spike."""

    NAVIGATION = "navigation"
    FINAL_SUBMIT = "final_submit"
    AMBIGUOUS = "ambiguous"


class FinalSubmitGuardError(RuntimeError):
    """Raised when the spike would activate a forbidden or ambiguous control."""


@dataclass(frozen=True)
class PageSignals:
    """Structural hints about the current application page.

    Prefer these over raw button labels when deciding whether "Apply" is
    entry navigation vs a final confirmation.
    """

    url: str = ""
    heading_text: str = ""
    step_label: str = ""
    looks_like_job_detail: bool = False
    looks_like_application_form: bool = False
    looks_like_review_or_confirmation: bool = False
    has_visible_resume_upload: bool = False
    has_summary_of_answers: bool = False


# Irreversible final submission — refuse always.
_FINAL_LABEL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^submit$",
        r"^submit\s+(my\s+)?application$",
        r"^send\s+(my\s+)?application$",
        r"^confirm\s+(and\s+)?(submit|apply)$",
        r"^confirm\s+application$",
        r"^finali[sz]e\s+application$",
        r"^place\s+application$",
        r"^submit\s+for\s+review$",
        r"^review\s+and\s+submit$",
        r"^submit\s+application$",
    )
)

# Safe to activate when advancing through an application (category A).
_NAV_LABEL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^continue$",
        r"^next$",
        r"^next\s+step$",
        r"^save\s+and\s+continue$",
        r"^save\s+&\s+continue$",
        r"^review(\s+application)?$",
        r"^back$",
        r"^previous$",
        r"^add\s+more$",
        r"^upload$",
        r"^choose\s+file$",
        r"^browse$",
        r"^how\s+to\s+apply$",
    )
)

# Labels that are navigation on job-detail / early form, but final on review pages.
# SEEK commonly uses "Quick apply" on the job detail page (entry, not final submit).
_CONTEXT_SENSITIVE_APPLY = re.compile(
    r"^((quick\s+)?apply(\s+now)?|apply\s+for\s+this\s+job)$",
    re.IGNORECASE,
)

_REVIEW_HEADING = re.compile(
    r"\b(review|confirm|summary|check\s+your\s+(application|answers)|almost\s+done)\b",
    re.IGNORECASE,
)


def normalize_control_label(text: str | None) -> str:
    """Collapse whitespace and strip invisible format chars for classification."""
    if not text:
        return ""
    # SEEK sometimes injects word-joiners (U+2060) into button labels.
    cleaned = "".join(
        ch for ch in text if ch not in {"\u2060", "\ufeff", "\u200b", "\u200c", "\u200d"}
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def derive_review_signals(page: PageSignals) -> PageSignals:
    """Enrich page signals using heading/step text when callers omit flags."""
    blob = f"{page.heading_text} {page.step_label}"
    review = page.looks_like_review_or_confirmation or bool(
        _REVIEW_HEADING.search(blob)
    )
    if page.has_summary_of_answers:
        review = True
    return PageSignals(
        url=page.url,
        heading_text=page.heading_text,
        step_label=page.step_label,
        looks_like_job_detail=page.looks_like_job_detail,
        looks_like_application_form=page.looks_like_application_form,
        looks_like_review_or_confirmation=review,
        has_visible_resume_upload=page.has_visible_resume_upload,
        has_summary_of_answers=page.has_summary_of_answers,
    )


def classify_control(label: str | None, *, page: PageSignals) -> ControlClass:
    """Classify whether activating a control is allowed, forbidden, or ambiguous."""
    text = normalize_control_label(label)
    if not text:
        return ControlClass.AMBIGUOUS

    page = derive_review_signals(page)

    for pattern in _FINAL_LABEL_PATTERNS:
        if pattern.search(text):
            return ControlClass.FINAL_SUBMIT

    for pattern in _NAV_LABEL_PATTERNS:
        if pattern.fullmatch(text) or pattern.search(text):
            # "Review" alone is navigation toward review, not submit.
            return ControlClass.NAVIGATION

    if _CONTEXT_SENSITIVE_APPLY.fullmatch(text):
        if page.looks_like_review_or_confirmation:
            return ControlClass.FINAL_SUBMIT
        if page.looks_like_job_detail:
            return ControlClass.NAVIGATION
        if page.looks_like_application_form and not page.looks_like_review_or_confirmation:
            # Mid-flow "Apply" without review cues is ambiguous on SEEK-like UIs.
            return ControlClass.AMBIGUOUS
        # Default: treat first Apply on unknown page as ambiguous rather than auto-click.
        if "seek.com" in page.url.lower() and "/job/" in page.url.lower():
            return ControlClass.NAVIGATION
        return ControlClass.AMBIGUOUS

    # Bare "Send" / "Complete" without "application" — ambiguous.
    if re.fullmatch(r"(send|complete|done|finish)", text, re.IGNORECASE):
        if page.looks_like_review_or_confirmation:
            return ControlClass.FINAL_SUBMIT
        return ControlClass.AMBIGUOUS

    if re.search(r"\bsubmit\b", text, re.IGNORECASE):
        return ControlClass.FINAL_SUBMIT

    return ControlClass.AMBIGUOUS


def assert_may_activate(label: str | None, *, page: PageSignals) -> ControlClass:
    """Allow only NAVIGATION. Refuse FINAL_SUBMIT and AMBIGUOUS."""
    kind = classify_control(label, page=page)
    if kind is ControlClass.NAVIGATION:
        return kind
    if kind is ControlClass.FINAL_SUBMIT:
        raise FinalSubmitGuardError(
            f"AAS-0 submit guard refused final-submission control: {label!r}. "
            "Spike must stop before irreversible submit. Owner clicks Submit manually."
        )
    raise FinalSubmitGuardError(
        f"AAS-0 submit guard cannot confidently classify control: {label!r}. "
        "STOP and ask the owner before activating. "
        f"page_signals={page!r}"
    )


def is_final_submit_control(label: str | None, *, page: PageSignals) -> bool:
    """True when classification is FINAL_SUBMIT."""
    return classify_control(label, page=page) is ControlClass.FINAL_SUBMIT
