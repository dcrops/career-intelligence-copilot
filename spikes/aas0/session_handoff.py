"""AAS spike helpers: final-review handoff, submission observation, CV rotation class."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class CvRotationClass(str, Enum):
    REPLACEABLE_TAILORED = "replaceable_tailored"
    PROTECT = "protect"
    AMBIGUOUS = "ambiguous"


# Internal CIC opportunity stems uploaded to SEEK during AAS-0 dogfood.
_OPP_STEM = re.compile(r"^opp_[0-9A-HJKMNP-TV-Z]{26}(\.pdf)?$", re.I)
# Future external export pattern (proposed) — underscore form only, not free-text titles.
_EXTERNAL_TAILORED = re.compile(
    r"^david_cropper_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*_(cv|cover_letter)\.pdf$",
    re.I,
)
# Conservative protect list — master/general CVs must not be auto-deleted.
_PROTECT_NAMES = frozenset(
    {
        "david cropper cv.pdf",
        "david_cropper_cv.pdf",
        "master cv.pdf",
        "master_cv.pdf",
        "general cv.pdf",
        "general_cv.pdf",
    }
)

_SUBMIT_SUCCESS_HINTS = (
    "application submitted",
    "application has been submitted",
    "successfully applied",
    "thanks for applying",
    "thank you for applying",
    "we've received your application",
    "we have received your application",
)

_FINAL_SUBMIT_LABELS = (
    "submit application",
    "submit your application",
)


@dataclass(frozen=True)
class FinalReviewHandoff:
    """Result of stopping automation at Review while keeping the browser open."""

    final_submit_control_visible: bool
    browser_kept_open_for_owner: bool
    automation_stopped: bool
    submit_clicked_by_automation: bool = False


@dataclass(frozen=True)
class SubmissionObservation:
    """Passive observation after owner may have submitted (automation never clicks)."""

    observed: bool
    evidence: str = ""
    status: Literal[
        "not_completed",
        "likely_submitted",
        "unknown",
    ] = "not_completed"


def looks_like_final_submit_label(label: str | None) -> bool:
    text = re.sub(r"\s+", " ", (label or "")).strip().lower()
    # Strip SEEK word-joiners if present in callers' labels.
    text = text.replace("\u2060", "")
    return any(text == hint or text.startswith(hint) for hint in _FINAL_SUBMIT_LABELS)


def build_final_review_handoff(*, final_submit_control_visible: bool) -> FinalReviewHandoff:
    """Automation stops; browser must remain open for owner Submit."""
    return FinalReviewHandoff(
        final_submit_control_visible=final_submit_control_visible,
        browser_kept_open_for_owner=True,
        automation_stopped=True,
        submit_clicked_by_automation=False,
    )


def observe_submission_from_page_text(body_text: str) -> SubmissionObservation:
    """Classify post-submit page text without activating any control."""
    lowered = (body_text or "").lower()
    for hint in _SUBMIT_SUCCESS_HINTS:
        if hint in lowered:
            return SubmissionObservation(
                observed=True,
                evidence=hint,
                status="likely_submitted",
            )
    if "submit application" in lowered or "review and submit" in lowered:
        return SubmissionObservation(
            observed=False,
            evidence="still_on_review_or_submit_visible",
            status="not_completed",
        )
    return SubmissionObservation(
        observed=False,
        evidence="no_clear_submission_signal",
        status="unknown",
    )


def classify_seek_cv_for_rotation(filename: str) -> CvRotationClass:
    """Conservative classification for disposable tailored CV rotation.

    Only DELETE candidates that CIC can confidently identify as replaceable
    tailored/application CVs. Ambiguous and master/general documents are protected.
    """
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name:
        return CvRotationClass.AMBIGUOUS
    lower = name.lower()
    if lower in _PROTECT_NAMES:
        return CvRotationClass.PROTECT
    if _OPP_STEM.match(name):
        return CvRotationClass.REPLACEABLE_TAILORED
    # Machine export names only (underscores). Spacey free titles stay ambiguous.
    if _EXTERNAL_TAILORED.match(name):
        return CvRotationClass.REPLACEABLE_TAILORED
    if lower.endswith(".pdf") and "cv" in lower:
        return CvRotationClass.AMBIGUOUS
    return CvRotationClass.AMBIGUOUS


def propose_external_export_filename(
    *,
    full_name: str,
    company: str,
    title: str,
    kind: Literal["cv", "cover_letter"],
) -> str:
    """Proposed employer-facing PDF name (packaging/export ownership — not browser)."""

    def slug(value: str) -> str:
        cleaned = re.sub(r"[^\w\s-]+", "", value, flags=re.UNICODE)
        cleaned = re.sub(r"[\s_-]+", "_", cleaned.strip())
        return cleaned.strip("_")

    base = f"{slug(full_name)}_{slug(company)}_{slug(title)}"
    suffix = "CV" if kind == "cv" else "Cover_Letter"
    return f"{base}_{suffix}.pdf"


def may_auto_delete_seek_cv(filename: str) -> bool:
    return classify_seek_cv_for_rotation(filename) is CvRotationClass.REPLACEABLE_TAILORED
