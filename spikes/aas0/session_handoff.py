"""AAS spike helpers: final-review handoff, submission observation, CV rotation class."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .answer_policy import is_default_resume_checkbox_label  # noqa: F401
from .resume_lifecycle import (  # noqa: F401
    CleanupCandidate,
    CvRotationClass,
    DefaultChangeResult,
    DefaultResumeChangedError,
    ResumeCapacityError,
    SeekResumeEntry,
    SeekResumeSnapshot,
    classify_seek_cv_for_rotation,
    detect_resume_capacity_message,
    evaluate_default_change,
    may_auto_delete_seek_cv,
    select_cleanup_candidate,
)

_SUBMIT_SUCCESS_HINTS = (
    "application submitted",
    "application has been submitted",
    "application has been sent",
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


def apply_owner_session_submission_observation(
    metrics,
    *,
    body_text: str,
    url: str = "",
) -> SubmissionObservation:
    """Record post-OWNER_END_SESSION page evidence. Never infers Submit from teardown."""
    metrics.submit_clicked = False
    observation = observe_submission_from_page_text(body_text, url=url)
    metrics.application_submission = observation.status
    metrics.submission_observation_evidence = observation.evidence
    return observation


def observe_submission_from_page_text(
    body_text: str,
    *,
    url: str = "",
) -> SubmissionObservation:
    """Classify post-submit page without activating any control.

    Success is the apply-success URL or a small allow-list of visible phrases.
    Stepper text ``Review and submit`` alone is not success.
    """
    lowered_url = (url or "").lower()
    if "/apply/success" in lowered_url:
        return SubmissionObservation(
            observed=True,
            evidence="apply_success_url",
            status="likely_submitted",
        )
    lowered = (body_text or "").lower()
    for hint in _SUBMIT_SUCCESS_HINTS:
        if hint in lowered:
            return SubmissionObservation(
                observed=True,
                evidence=hint,
                status="likely_submitted",
            )
    if "submit application" in lowered:
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


def propose_external_export_filename(
    *,
    full_name: str,
    company: str,
    title: str,
    kind: Literal["cv", "cover_letter"],
) -> str:
    """Obsolete underscore helper. Production uploads use spaced export names."""

    def slug(value: str) -> str:
        cleaned = re.sub(r"[^\w\s-]+", "", value, flags=re.UNICODE)
        cleaned = re.sub(r"[\s_-]+", "_", cleaned.strip())
        return cleaned.strip("_")

    base = f"{slug(full_name)}_{slug(company)}_{slug(title)}"
    suffix = "CV" if kind == "cv" else "Cover_Letter"
    return f"{base}_{suffix}.pdf"
