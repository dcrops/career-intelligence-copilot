"""Unit tests for FR-008 M1/M2 ApplicationWorkflowRunner."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.orchestration import (
    InMemoryCheckpointStore,
    PasteJobInput,
    WorkflowResumeError,
    completed_spike_nodes,
)
from tests.unit.orchestration.m1_helpers import (
    fixture_job_input,
    offline_runner,
)


def test_start_stops_at_owner_review(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    state = runner.start(fixture_job_input())
    assert state.status == "awaiting_owner"
    assert state.approval.pending_kind == "owner_review"
    assert set(state.approval.pending_options) == {"apply", "skip", "defer"}
    assert completed_spike_nodes(state) == [
        "acquire",
        "validate_normalise",
        "analyse",
        "assess",
        "match",
        "strategy",
        "persist",
        "owner_review",
    ]
    assert state.artefacts.strategy is not None
    # FR-009 M1: the Opportunity is durable before the interrupt.
    assert state.artefacts.opportunity_id is not None
    awaiting = runner.opportunities.get(state.artefacts.opportunity_id)
    assert awaiting.decision is None
    assert state.acquisition is not None
    assert state.acquisition.source_kind == "paste"


def test_execution_events_include_required_types(tmp_path: Path) -> None:
    state = offline_runner(opportunities_dir=tmp_path / "opps").start(fixture_job_input())
    types = [event.event_type for event in state.execution.events]
    assert types[0] == "run_started"
    assert "node_started" in types
    assert "node_succeeded" in types
    assert "checkpoint_written" in types
    assert "approval_requested" in types
    assert "run_completed" not in types


def test_resume_apply_persists_one_opportunity(tmp_path: Path) -> None:
    store = InMemoryCheckpointStore()
    opps = tmp_path / "opps"
    runner = offline_runner(store=store, opportunities_dir=opps)
    paused = runner.start(fixture_job_input())
    done = runner.resume(paused.run_id, "apply")
    assert done.status == "completed"
    assert done.approval.owner_decision == "apply"
    assert done.artefacts.opportunity_id == paused.artefacts.opportunity_id
    opportunity = runner.opportunities.get(done.artefacts.opportunity_id)
    assert opportunity.decision is not None
    assert opportunity.decision.decision == "apply"
    assert opportunity.decision.notes == f"workflow_run_id={done.run_id}"
    assert len(opportunity.artifact_paths) == 5
    assert "persist" in completed_spike_nodes(done)
    assert "record_decision" in completed_spike_nodes(done)
    assert len(runner.opportunities.list_opportunities()) == 1


def test_resume_apply_idempotent_repeat(tmp_path: Path) -> None:
    store = InMemoryCheckpointStore()
    runner = offline_runner(store=store, opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    first = runner.resume(paused.run_id, "apply")
    second = runner.resume(first.run_id, "apply")
    assert second.run_id == first.run_id
    assert second.artefacts.opportunity_id == first.artefacts.opportunity_id
    assert len(runner.opportunities.list_opportunities()) == 1


def test_resume_skip_and_defer_preserve_the_same_opportunity(tmp_path: Path) -> None:
    for decision in ("skip", "defer"):
        runner = offline_runner(opportunities_dir=tmp_path / decision)
        paused = runner.start(fixture_job_input())
        pre_review_id = paused.artefacts.opportunity_id
        done = runner.resume(paused.run_id, decision)  # type: ignore[arg-type]
        assert done.status == "completed"
        assert done.approval.owner_decision == decision
        assert done.artefacts.opportunity_id == pre_review_id
        assert len(runner.opportunities.list_opportunities()) == 1
        assert "persist" in completed_spike_nodes(done)
        assert "record_decision" in completed_spike_nodes(done)
        opportunity = runner.opportunities.get(pre_review_id)  # type: ignore[arg-type]
        assert opportunity.decision is not None
        assert opportunity.decision.decision == decision


def test_invalid_resume_fails_closed(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    with pytest.raises(WorkflowResumeError):
        runner.resume(paused.run_id, "approve")  # type: ignore[arg-type]
    reloaded = runner.store.load(paused.run_id)
    assert reloaded.status == "awaiting_owner"
    assert reloaded.approval.owner_decision is None


def test_cannot_change_decision_after_accept(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    done = runner.resume(paused.run_id, "apply")
    with pytest.raises(WorkflowResumeError):
        runner.resume(done.run_id, "skip")


def test_empty_job_fails_without_artefacts(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    state = runner.start(PasteJobInput(raw_text="   "))
    assert state.status == "failed"
    assert state.artefacts.job_analysis is None
    assert state.control.last_error is not None


def test_cancel_awaiting_run(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    cancelled = runner.cancel(paused.run_id)
    assert cancelled.status == "cancelled"
