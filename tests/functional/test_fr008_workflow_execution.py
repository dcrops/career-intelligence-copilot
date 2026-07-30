"""Functional acceptance: FR-008 M1 workflow execution interrupt."""

from __future__ import annotations

from career_intelligence.orchestration import ApplicationWorkflowRunner
from tests.unit.orchestration.m1_helpers import fixture_job_input, offline_runner


def test_golden_workflow_stops_at_owner_review_without_terminal_continuation(
    tmp_path,
) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    state = runner.start(fixture_job_input())

    assert state.status == "awaiting_owner"
    assert state.approval.pending_kind == "owner_review"
    assert state.approval.owner_decision is None
    assert state.artefacts.profile is not None
    assert state.artefacts.posting is not None
    assert state.artefacts.job_analysis is not None
    assert state.artefacts.assessment is not None
    assert state.artefacts.portfolio_match is not None
    assert state.artefacts.strategy is not None
    # FR-009 M1: durable before the interrupt, still undecided.
    assert state.artefacts.opportunity_id is not None
    assert runner.opportunities.get(state.artefacts.opportunity_id).decision is None

    event_types = [event.event_type for event in state.execution.events]
    assert event_types.count("run_started") == 1
    assert "approval_requested" in event_types
    assert "run_completed" not in event_types
    assert "approval_received" not in event_types

    # No default decision — reloaded checkpoint remains awaiting.
    reloaded = runner.store.load(state.run_id)
    assert reloaded.status == "awaiting_owner"
    assert reloaded.approval.owner_decision is None


def test_public_runner_api_surface() -> None:
    assert hasattr(ApplicationWorkflowRunner, "start")
    assert hasattr(ApplicationWorkflowRunner, "resume")
    assert hasattr(ApplicationWorkflowRunner, "cancel")
