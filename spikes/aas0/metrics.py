"""Timing and form statistics for AAS-0 (owner attention is primary)."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


FieldOutcome = Literal[
    "auto",
    "owner",
    "unknown",
    "failed",
    "skipped",
]


@dataclass
class FieldRecord:
    label: str
    outcome: FieldOutcome
    detail: str = ""
    value_preview: str = ""


@dataclass
class SpikeMetrics:
    """Separate elapsed / automation / wait / owner-attention clocks."""

    opportunity_id: str
    started_at_monotonic: float = field(default_factory=time.monotonic)
    automation_seconds: float = 0.0
    waiting_seconds: float = 0.0
    owner_attention_seconds: float = 0.0
    fields: list[FieldRecord] = field(default_factory=list)
    pages_traversed: int = 0
    documents_uploaded: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    final_stage_reached: str = ""
    submit_clicked: bool = False
    browser_kept_open_for_owner: bool = False
    application_submission: str = "not_completed"
    submission_observation_evidence: str = ""
    notes: list[str] = field(default_factory=list)
    default_resume_before: str | None = None
    default_resume_after_upload: str | None = None
    default_resume_at_handoff: str | None = None
    default_observable_before: bool = False
    default_observable_after_upload: bool = False
    default_observable_at_handoff: bool = False
    default_changed_unexpected: bool = False
    default_change_reason: str = ""
    default_checkbox_reason: str = ""
    default_checkbox_still_checked: bool = False
    default_checkbox_uncheck_threw: bool = False
    default_checkbox_baseline: str | None = None
    default_checkbox_settled_default: str | None = None
    default_checkbox_settle_poll_count: int = 0
    default_checkbox_settle_wait_ms: int = 0
    resume_capacity_blocked: bool = False
    resume_capacity_evidence: str = ""
    cleanup_candidate: str | None = None
    cleanup_candidate_reason: str = ""
    resume_list_before: list[dict[str, object]] = field(default_factory=list)
    resume_list_after: list[dict[str, object]] = field(default_factory=list)
    expected_cv_filename: str = ""
    expected_cover_letter_filename: str = ""
    selected_resume_before: str | None = None
    selected_resume_after_upload: str | None = None
    cv_selection_reason: str = ""
    upload_completion_reason: str = ""
    review_observed_cv: str | None = None
    review_observed_cover_letter: str | None = None
    review_document_reason: str = ""
    resume_rotation_attempted: bool = False
    resume_rotation_reason: str = ""
    resume_deleted_filename: str | None = None
    resume_rotation_retry_attempted: bool = False
    resume_rotation_retry_outcome: str = ""
    cleanup_skips: list[dict[str, object]] = field(default_factory=list)
    upload_failure_reason: str = ""
    expected_cv_selected: bool = False
    resume_default_before_deletion: str | None = None
    resume_default_after_deletion: str | None = None
    resume_delete_verification_poll_count: int = 0
    resume_delete_verification_wait_ms: int = 0
    resume_delete_verification_reason: str = ""
    resume_list_count_before: int = 0
    resume_list_count_after_deletion: int = 0

    def record_field(
        self,
        label: str,
        outcome: FieldOutcome,
        *,
        detail: str = "",
        value_preview: str = "",
    ) -> None:
        preview = value_preview
        if len(preview) > 80:
            preview = preview[:77] + "..."
        self.fields.append(
            FieldRecord(
                label=label,
                outcome=outcome,
                detail=detail,
                value_preview=preview,
            )
        )

    def add_failure(self, message: str) -> None:
        self.failures.append(message)

    def add_note(self, message: str) -> None:
        self.notes.append(message)

    def record_review_document_gate(
        self,
        *,
        observed_cv: str | None,
        observed_cover_letter: str | None,
        reason: str,
    ) -> None:
        """Record the Review filename invariant without changing its semantics."""
        self.review_observed_cv = observed_cv
        self.review_observed_cover_letter = observed_cover_letter
        self.review_document_reason = reason

    def add_automation(self, seconds: float) -> None:
        self.automation_seconds += max(0.0, seconds)

    def add_waiting(self, seconds: float) -> None:
        self.waiting_seconds += max(0.0, seconds)

    def add_owner_attention(self, seconds: float) -> None:
        self.owner_attention_seconds += max(0.0, seconds)

    def elapsed_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.started_at_monotonic)

    def counts(self) -> dict[str, int]:
        totals: dict[str, int] = {
            "total": len(self.fields),
            "auto": 0,
            "owner": 0,
            "unknown": 0,
            "failed": 0,
            "skipped": 0,
        }
        for row in self.fields:
            totals[row.outcome] = totals.get(row.outcome, 0) + 1
        return totals

    def to_dict(self) -> dict[str, Any]:
        counts = self.counts()
        return {
            "opportunity_id": self.opportunity_id,
            "timing": {
                "total_elapsed_seconds": round(self.elapsed_seconds(), 2),
                "automation_seconds": round(self.automation_seconds, 2),
                "waiting_seconds": round(self.waiting_seconds, 2),
                "owner_active_attention_seconds": round(
                    self.owner_attention_seconds, 2
                ),
                "owner_active_attention_minutes": round(
                    self.owner_attention_seconds / 60.0, 2
                ),
                "primary_metric": "owner_active_attention_seconds",
            },
            "form": {
                "fields_encountered": counts["total"],
                "fields_auto": counts["auto"],
                "fields_owner": counts["owner"],
                "fields_unknown": counts["unknown"],
                "fields_failed": counts["failed"],
                "fields_skipped": counts["skipped"],
                "documents_uploaded": list(self.documents_uploaded),
                "pages_traversed": self.pages_traversed,
            },
            "fields": [asdict(f) for f in self.fields],
            "failures": list(self.failures),
            "screenshots": list(self.screenshots),
            "final_stage_reached": self.final_stage_reached,
            "submit_clicked": self.submit_clicked,
            "browser_kept_open_for_owner": self.browser_kept_open_for_owner,
            "application_submission": self.application_submission,
            "submission_observation_evidence": self.submission_observation_evidence,
            "resume_lifecycle": {
                "default_resume_before": self.default_resume_before,
                "default_resume_after_upload": self.default_resume_after_upload,
                "default_resume_at_handoff": self.default_resume_at_handoff,
                "default_observable_before": self.default_observable_before,
                "default_observable_after_upload": self.default_observable_after_upload,
                "default_observable_at_handoff": self.default_observable_at_handoff,
                "default_changed_unexpected": self.default_changed_unexpected,
                "default_change_reason": self.default_change_reason,
                "default_checkbox_reason": self.default_checkbox_reason,
                "default_checkbox_still_checked": self.default_checkbox_still_checked,
                "default_checkbox_uncheck_threw": self.default_checkbox_uncheck_threw,
                "default_checkbox_baseline": self.default_checkbox_baseline,
                "default_checkbox_settled_default": self.default_checkbox_settled_default,
                "default_checkbox_settle_poll_count": (
                    self.default_checkbox_settle_poll_count
                ),
                "default_checkbox_settle_wait_ms": self.default_checkbox_settle_wait_ms,
                "resume_capacity_blocked": self.resume_capacity_blocked,
                "resume_capacity_evidence": self.resume_capacity_evidence,
                "cleanup_candidate": self.cleanup_candidate,
                "cleanup_candidate_reason": self.cleanup_candidate_reason,
                "resume_list_before": list(self.resume_list_before),
                "resume_list_after": list(self.resume_list_after),
                "expected_cv_filename": self.expected_cv_filename,
                "expected_cover_letter_filename": self.expected_cover_letter_filename,
                "selected_resume_before": self.selected_resume_before,
                "selected_resume_after_upload": self.selected_resume_after_upload,
                "cv_selection_reason": self.cv_selection_reason,
                "upload_completion_reason": self.upload_completion_reason,
                "review_observed_cv": self.review_observed_cv,
                "review_observed_cover_letter": self.review_observed_cover_letter,
                "review_document_reason": self.review_document_reason,
                "resume_rotation_attempted": self.resume_rotation_attempted,
                "resume_rotation_reason": self.resume_rotation_reason,
                "resume_deleted_filename": self.resume_deleted_filename,
                "resume_rotation_retry_attempted": self.resume_rotation_retry_attempted,
                "resume_rotation_retry_outcome": self.resume_rotation_retry_outcome,
                "cleanup_skips": list(self.cleanup_skips),
                "upload_failure_reason": self.upload_failure_reason,
                "expected_cv_selected": self.expected_cv_selected,
                "resume_default_before_deletion": self.resume_default_before_deletion,
                "resume_default_after_deletion": self.resume_default_after_deletion,
                "resume_delete_verification_poll_count": (
                    self.resume_delete_verification_poll_count
                ),
                "resume_delete_verification_wait_ms": (
                    self.resume_delete_verification_wait_ms
                ),
                "resume_delete_verification_reason": (
                    self.resume_delete_verification_reason
                ),
                "resume_list_count_before": self.resume_list_count_before,
                "resume_list_count_after_deletion": (
                    self.resume_list_count_after_deletion
                ),
            },
            "notes": list(self.notes),
            "manual_comparison_prompt": (
                "Owner should estimate minutes for the same application fully "
                "manually after the spike for comparison."
            ),
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")


class TimedPhase:
    """Context manager that accumulates seconds into a metrics bucket."""

    def __init__(self, metrics: SpikeMetrics, bucket: str) -> None:
        self._metrics = metrics
        self._bucket = bucket
        self._start = 0.0

    def __enter__(self) -> TimedPhase:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: object) -> None:
        elapsed = time.monotonic() - self._start
        if self._bucket == "automation":
            self._metrics.add_automation(elapsed)
        elif self._bucket == "waiting":
            self._metrics.add_waiting(elapsed)
        elif self._bucket == "owner":
            self._metrics.add_owner_attention(elapsed)
