"""Unit tests for M2 decision and outcome logging via OpportunityService."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest

from career_intelligence.opportunities import (
    OpportunityService,
    OpportunityTransitionError,
    OpportunityValidationError,
)

from .helpers import create_opportunity


def test_record_decision_apply_skip_defer(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    updated = service.record_decision(opportunity.opportunity_id, "apply", notes="Go")
    assert updated.decision is not None
    assert updated.decision.decision == "apply"
    assert updated.decision.notes == "Go"
    assert updated.decision.decided_at is not None
    assert updated.status == "assessed"  # decision does not change status

    skipped = service.record_decision(opportunity.opportunity_id, "skip")
    assert skipped.decision is not None
    assert skipped.decision.decision == "skip"

    deferred = service.record_decision(opportunity.opportunity_id, "defer")
    assert deferred.decision is not None
    assert deferred.decision.decision == "defer"


def test_record_decision_rejects_invalid(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    with pytest.raises(OpportunityValidationError):
        service.record_decision(opportunity.opportunity_id, "maybe")  # type: ignore[arg-type]


def test_update_outcome_status_and_kind(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    service.record_decision(opportunity.opportunity_id, "apply")
    submitted = service.update_outcome(
        opportunity.opportunity_id,
        status="submitted",
        outcome="pending",
        notes="Applied via LinkedIn",
    )
    assert submitted.status == "submitted"
    assert submitted.outcome is not None
    assert submitted.outcome.outcome == "pending"
    assert submitted.outcome.notes == "Applied via LinkedIn"

    interviewing = service.update_outcome(
        opportunity.opportunity_id,
        status="interviewing",
        interview_stage="recruiter",
        follow_up_date=date(2026, 8, 1),
    )
    assert interviewing.status == "interviewing"
    assert interviewing.outcome is not None
    assert interviewing.outcome.interview_stage == "recruiter"
    assert interviewing.outcome.follow_up_date == date(2026, 8, 1)
    assert interviewing.outcome.outcome == "pending"  # preserved


def test_invalid_status_transition_rejected(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    with pytest.raises(OpportunityTransitionError, match="interviewing"):
        service.update_outcome(opportunity.opportunity_id, status="interviewing")


def test_terminal_status_cannot_reopen(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    service.update_outcome(opportunity.opportunity_id, status="submitted")
    service.update_outcome(opportunity.opportunity_id, status="rejected", outcome="rejected")
    with pytest.raises(OpportunityTransitionError, match="terminal"):
        service.update_outcome(opportunity.opportunity_id, status="interviewing")


def test_round_trip_reload(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    service.record_decision(opportunity.opportunity_id, "apply")
    service.update_outcome(
        opportunity.opportunity_id,
        status="submitted",
        outcome="pending",
    )
    reloaded = OpportunityService.from_path(tmp_path).get(opportunity.opportunity_id)
    assert reloaded.decision is not None
    assert reloaded.decision.decision == "apply"
    assert reloaded.status == "submitted"
    assert reloaded.outcome is not None
    assert reloaded.outcome.outcome == "pending"


def test_repeated_updates_and_snapshots_untouched(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    artifact_dir = tmp_path / "artifacts" / opportunity.opportunity_id
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in artifact_dir.iterdir()
    }

    service.record_decision(opportunity.opportunity_id, "apply")
    service.update_outcome(opportunity.opportunity_id, status="preparing")
    service.update_outcome(opportunity.opportunity_id, status="submitted", outcome="pending")
    service.update_outcome(
        opportunity.opportunity_id,
        status="interviewing",
        interview_stage="technical",
    )

    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in artifact_dir.iterdir()
    }
    assert before == after


def test_update_outcome_requires_at_least_one_field(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    with pytest.raises(OpportunityValidationError):
        service.update_outcome(opportunity.opportunity_id)
