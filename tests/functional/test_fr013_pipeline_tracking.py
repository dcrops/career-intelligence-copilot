"""Functional tests for FR-013 M2 pipeline tracking coordination."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.pipeline import (
    JsonDirectoryPipelineEventStore,
    PipelineEvidence,
    PipelinePartialWriteError,
    PipelineTrackingService,
    new_pipeline_event_id,
)
from career_intelligence.opportunities import OpportunityService
from tests.unit.opportunities.helpers import create_opportunity
from tests.unit.pipeline.helpers_m2 import CountingFailStore


def test_fr013_m2_event_first_round_trip(tmp_path: Path) -> None:
    opportunities, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    events = JsonDirectoryPipelineEventStore(tmp_path / "pipeline_events")
    tracking = PipelineTrackingService(opportunities=opportunities, events=events)
    opp_id = opportunity.opportunity_id
    now = datetime(2026, 8, 5, 8, 0, 0, tzinfo=UTC)

    tracking.advance_status(
        opp_id, "preparing", evidence=PipelineEvidence(note="prep"), occurred_at=now
    )
    tracking.record_submitted(
        opp_id,
        evidence=PipelineEvidence(note="sent", submitted_at=now, channel="manual"),
        occurred_at=now,
    )
    tracking.advance_status(
        opp_id, "interviewing", evidence=PipelineEvidence(note="screen"), occurred_at=now
    )
    tracking.change_interview_stage(opp_id, "recruiter")

    reloaded = PipelineTrackingService.from_paths(
        opportunities_root=tmp_path / "opportunities",
        events_root=tmp_path / "pipeline_events",
    )
    current = reloaded.get_opportunity(opp_id)
    assert current.status == "interviewing"
    assert current.outcome is not None
    assert current.outcome.interview_stage == "recruiter"
    assert len(reloaded.list_events(opp_id)) == 4
    assert reloaded.detect_divergence(opp_id).divergent is False


def test_fr013_m2_partial_write_recovery(tmp_path: Path) -> None:
    opportunities, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    flaky = CountingFailStore(opportunities._store, fail_on_save=1)  # noqa: SLF001
    wrapped = OpportunityService(store=flaky)
    events = JsonDirectoryPipelineEventStore(tmp_path / "pipeline_events")
    tracking = PipelineTrackingService(opportunities=wrapped, events=events)
    event_id = new_pipeline_event_id()

    try:
        tracking.advance_status(
            opportunity.opportunity_id,
            "deferred",
            evidence=PipelineEvidence(note="park"),
            event_id=event_id,
        )
        raised = None
    except PipelinePartialWriteError as error:
        raised = error

    assert raised is not None
    assert events.exists(event_id)
    assert wrapped.get(opportunity.opportunity_id).status == "assessed"

    flaky._fail_on_save = -1  # noqa: SLF001
    recovered = tracking.apply_stored_event(event_id)
    assert recovered.opportunity.status == "deferred"
    assert tracking.detect_divergence(opportunity.opportunity_id).divergent is False
