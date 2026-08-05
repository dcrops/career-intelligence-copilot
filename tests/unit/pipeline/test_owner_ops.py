"""Unit tests for FR-013 M3 owner-oriented PipelineTrackingService helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.pipeline import PipelineConsistencyError, PipelineEvidence
from tests.unit.pipeline.helpers_m2 import tracking_workspace


def test_list_pipeline_active_only(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    assert tracking.list_pipeline() == []
    tracking.advance_status(
        opportunity.opportunity_id,
        "preparing",
        evidence=PipelineEvidence(note="prep"),
    )
    active = tracking.list_pipeline()
    assert len(active) == 1
    assert tracking.list_pipeline(active_only=False)
    assert tracking.list_pipeline(status="assessed") == []


def test_record_interview_and_acknowledgement(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    oid = opportunity.opportunity_id
    with pytest.raises(PipelineConsistencyError):
        tracking.record_acknowledgement(oid)
    with pytest.raises(PipelineConsistencyError):
        tracking.record_interview(oid, "recruiter")

    tracking.record_submitted(
        oid,
        evidence=PipelineEvidence(note="sent", channel="manual"),
    )
    ack = tracking.record_acknowledgement(oid, note="auto-reply")
    assert ack.opportunity.status == "submitted"
    assert ack.opportunity_updated is False

    first = tracking.record_interview(oid, "recruiter")
    assert first.opportunity.status == "interviewing"
    second = tracking.record_interview(oid, "technical")
    assert second.opportunity.status == "interviewing"
    assert second.opportunity.outcome is not None
    assert second.opportunity.outcome.interview_stage == "technical"
