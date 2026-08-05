"""Unit tests for FR-013 M4 derived pipeline reporting."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from career_intelligence.pipeline import (
    PipelineEvidence,
    build_summary_report,
    export_pipeline_csv,
)
from tests.unit.pipeline.helpers_m2 import tracking_workspace

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)


def test_summary_report_counts_and_rates(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    oid = opportunity.opportunity_id
    tracking.record_submitted(
        oid,
        evidence=PipelineEvidence(note="sent", submitted_at=NOW),
        occurred_at=NOW,
    )
    tracking.record_interview(oid, "technical", occurred_at=NOW + timedelta(days=2))
    tracking.advance_status(
        oid,
        "offer",
        evidence=PipelineEvidence(note="offer"),
        outcome="offer",
        occurred_at=NOW + timedelta(days=5),
    )

    report = tracking.summary_report(as_of=NOW + timedelta(days=6))
    assert report.submitted_count == 1
    assert report.offer_count == 1
    assert report.by_status.get("offer") == 1
    assert report.offer_rate == 1.0
    assert report.historical_event_count >= 3
    assert report.ageing
    assert report.ageing[0].days_in_status is not None


def test_follow_ups_due_and_export(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    oid = opportunity.opportunity_id
    tracking.record_submitted(
        oid,
        evidence=PipelineEvidence(note="sent", submitted_at=NOW),
        occurred_at=NOW,
    )
    tracking.set_follow_up(oid, date(2026, 8, 1), occurred_at=NOW)

    due = tracking.follow_ups_due(reference_date=date(2026, 8, 5))
    assert len(due) == 1
    assert due[0].days_until_due < 0

    path = tracking.export_csv(tmp_path / "pipeline.csv")
    text = path.read_text(encoding="utf-8-sig")
    assert "opportunity_id" in text
    assert oid in text
    assert "submitted" in text


def test_build_summary_empty() -> None:
    report = build_summary_report([], as_of=NOW)
    assert report.total_opportunities == 0
    assert report.offer_rate is None
    assert export_pipeline_csv  # imported for continuity API surface
