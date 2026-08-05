"""Unit tests for FR-013 M2 PipelineTrackingService coordination."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from career_intelligence.pipeline import (
    JsonDirectoryPipelineEventStore,
    PipelineConsistencyError,
    PipelineDivergenceError,
    PipelineEvidence,
    PipelinePartialWriteError,
    PipelineTrackingService,
    PipelineValidationError,
    PackageEvidenceRef,
    new_pipeline_event_id,
)
from tests.unit.pipeline.helpers import ATTEMPT_A, FIXED_PREPARED
from tests.unit.pipeline.helpers_m2 import tracking_workspace, tracking_with_flaky_save

NOW = datetime(2026, 8, 5, 6, 0, 0, tzinfo=UTC)


def test_advance_and_record_submitted(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    opp_id = opportunity.opportunity_id

    preparing = tracking.advance_status(
        opp_id,
        "preparing",
        evidence=PipelineEvidence(note="start package"),
        occurred_at=NOW,
    )
    assert preparing.opportunity.status == "preparing"
    assert preparing.appended is True
    assert preparing.opportunity_updated is True

    submitted = tracking.record_submitted(
        opp_id,
        evidence=PipelineEvidence(
            note="owner attested",
            submission_attempt_id=ATTEMPT_A,
            submitted_at=NOW,
            package=PackageEvidenceRef(
                opportunity_id=opp_id,
                prepared_at=FIXED_PREPARED,
            ),
        ),
        occurred_at=NOW,
    )
    assert submitted.opportunity.status == "submitted"
    assert submitted.opportunity.outcome is not None
    assert submitted.opportunity.outcome.outcome == "pending"
    assert len(tracking.list_events(opp_id)) == 2


def test_validation_before_writes_rejects_illegal(tmp_path: Path) -> None:
    tracking, opportunities, opportunity, events = tracking_workspace(tmp_path)
    with pytest.raises(PipelineValidationError):
        tracking.advance_status(
            opportunity.opportunity_id,
            "interviewing",
            evidence=PipelineEvidence(note="skip"),
        )
    assert events.list() == []
    assert opportunities.get(opportunity.opportunity_id).status == "assessed"


def test_note_is_event_only(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    before = opportunity.updated_at
    result = tracking.add_note(opportunity.opportunity_id, "reflection")
    assert result.opportunity_updated is False
    assert result.opportunity.status == "assessed"
    assert len(tracking.list_events(opportunity.opportunity_id)) == 1
    # Opportunity row unchanged (no projection write).
    assert result.opportunity.updated_at == before


def test_partial_failure_then_idempotent_retry(tmp_path: Path) -> None:
    tracking, opportunities, opportunity, events, flaky = tracking_with_flaky_save(
        tmp_path,
        fail_on_save=1,
    )
    opp_id = opportunity.opportunity_id
    event_id = new_pipeline_event_id()

    with pytest.raises(PipelinePartialWriteError) as raised:
        tracking.advance_status(
            opp_id,
            "preparing",
            evidence=PipelineEvidence(note="prep"),
            event_id=event_id,
            occurred_at=NOW,
        )
    assert raised.value.event_id == event_id
    assert events.exists(event_id)
    assert opportunities.get(opp_id).status == "assessed"

    # Retry with same event id — skip append, complete Opportunity write.
    flaky._fail_on_save = -1  # noqa: SLF001 — disable further failures
    result = tracking.advance_status(
        opp_id,
        "preparing",
        evidence=PipelineEvidence(note="prep"),
        event_id=event_id,
        occurred_at=NOW,
    )
    assert result.appended is False
    assert result.opportunity_updated is True
    assert result.opportunity.status == "preparing"
    assert len(events.list(opportunity_id=opp_id)) == 1


def test_idempotent_complete_retry(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    event_id = new_pipeline_event_id()
    first = tracking.advance_status(
        opportunity.opportunity_id,
        "deferred",
        evidence=PipelineEvidence(note="later"),
        event_id=event_id,
        occurred_at=NOW,
    )
    second = tracking.advance_status(
        opportunity.opportunity_id,
        "deferred",
        evidence=PipelineEvidence(note="later"),
        event_id=event_id,
        occurred_at=NOW,
    )
    assert first.appended is True
    assert second.appended is False
    assert second.opportunity.status == "deferred"
    assert len(tracking.list_events(opportunity.opportunity_id)) == 1
    # Explicit recovery API
    third = tracking.apply_stored_event(event_id)
    assert third.appended is False
    assert third.opportunity.status == "deferred"


def test_conflicting_payload_same_id_rejected(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    event_id = new_pipeline_event_id()
    tracking.advance_status(
        opportunity.opportunity_id,
        "deferred",
        evidence=PipelineEvidence(note="a"),
        event_id=event_id,
        occurred_at=NOW,
    )
    from career_intelligence.pipeline import PipelineEvent

    conflict = PipelineEvent(
        event_id=event_id,
        opportunity_id=opportunity.opportunity_id,
        occurred_at=NOW,
        recorded_at=NOW,
        kind="status_transition",
        from_status="assessed",
        to_status="preparing",
        evidence=PipelineEvidence(note="b"),
    )
    with pytest.raises(PipelineConsistencyError):
        tracking.apply_event(conflict)


def test_stale_from_status_rejected(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    tracking.advance_status(
        opportunity.opportunity_id,
        "preparing",
        evidence=PipelineEvidence(note="prep"),
    )
    # Manually craft event with stale from_status via apply_event path using
    # advance which always uses current — use apply_event with wrong from.
    from career_intelligence.pipeline import PipelineEvent

    now = datetime.now(UTC)
    bad = PipelineEvent(
        event_id=new_pipeline_event_id(),
        opportunity_id=opportunity.opportunity_id,
        occurred_at=now,
        recorded_at=now,
        kind="status_transition",
        from_status="assessed",
        to_status="submitted",
        evidence=PipelineEvidence(note="stale", submitted_at=now),
    )
    with pytest.raises(PipelineConsistencyError):
        tracking.apply_event(bad)


def test_divergence_detection_and_reconcile(tmp_path: Path) -> None:
    tracking, opportunities, opportunity, events = tracking_workspace(tmp_path)
    opp_id = opportunity.opportunity_id
    tracking.advance_status(
        opp_id,
        "preparing",
        evidence=PipelineEvidence(note="prep"),
        occurred_at=NOW,
    )
    # Bypass tracking service — diverge Opportunity from events.
    opportunities.update_outcome(opp_id, status="submitted", outcome="pending")
    report = tracking.detect_divergence(opp_id)
    assert report.divergent is True
    assert report.expected_status == "preparing"
    assert report.actual_status == "submitted"

    with pytest.raises(PipelineDivergenceError):
        tracking.require_consistent(opp_id)

    reconciled = tracking.reconcile(opp_id)
    assert reconciled.status == "preparing"
    assert tracking.detect_divergence(opp_id).divergent is False


def test_terminal_correction(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    opp_id = opportunity.opportunity_id
    tracking.advance_status(opp_id, "submitted", evidence=PipelineEvidence(
        note="sent",
        submitted_at=NOW,
    ))
    tracking.advance_status(
        opp_id,
        "rejected",
        evidence=PipelineEvidence(note="no"),
        outcome="rejected",
    )
    assert tracking.get_opportunity(opp_id).status == "rejected"

    corrected = tracking.correct_status(
        opp_id,
        "submitted",
        note="mistaken rejection — still waiting",
        outcome="pending",
    )
    assert corrected.opportunity.status == "submitted"
    assert corrected.event.kind == "correction"
    assert corrected.opportunity.outcome is not None
    assert corrected.opportunity.outcome.outcome == "pending"


def test_interview_outcome_follow_up_consistency(tmp_path: Path) -> None:
    tracking, _, opportunity, _ = tracking_workspace(tmp_path)
    opp_id = opportunity.opportunity_id
    tracking.advance_status(
        opp_id,
        "submitted",
        evidence=PipelineEvidence(note="sent", submitted_at=NOW),
    )
    tracking.advance_status(opp_id, "interviewing", evidence=PipelineEvidence(note="loop"))
    tracking.change_interview_stage(opp_id, "technical")
    tracking.change_outcome(opp_id, "pending")
    tracking.set_follow_up(opp_id, date(2026, 8, 20))

    current = tracking.get_opportunity(opp_id)
    assert current.status == "interviewing"
    assert current.outcome is not None
    assert current.outcome.interview_stage == "technical"
    assert current.outcome.follow_up_date == date(2026, 8, 20)
    assert tracking.detect_divergence(opp_id).divergent is False


def test_no_submission_attempt_auto_advance_api(tmp_path: Path) -> None:
    tracking, _, _, _ = tracking_workspace(tmp_path)
    assert not hasattr(tracking, "advance_from_submission_attempt")
    assert not hasattr(tracking, "on_submission_success")


def test_json_store_coordination(tmp_path: Path) -> None:
    from tests.unit.opportunities.helpers import create_opportunity

    opportunities, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    events = JsonDirectoryPipelineEventStore(tmp_path / "pipeline_events")
    tracking = PipelineTrackingService(opportunities=opportunities, events=events)
    result = tracking.advance_status(
        opportunity.opportunity_id,
        "deferred",
        evidence=PipelineEvidence(note="park"),
    )
    reloaded = PipelineTrackingService(opportunities=opportunities, events=events)
    assert reloaded.get_opportunity(opportunity.opportunity_id).status == "deferred"
    assert len(reloaded.list_events(opportunity.opportunity_id)) == 1
    assert result.event.event_id.startswith("ple_")
