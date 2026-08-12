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
