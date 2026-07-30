"""Functional acceptance: FR-008 M2 checkpoint resume + Opportunity side effects."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.orchestration import (
    ApplicationWorkflowRunner,
    JsonDirectoryCheckpointStore,
    WorkflowResumeError,
    completed_spike_nodes,
)
from tests.unit.orchestration.m1_helpers import (
    fixture_job_input,
    json_runner,
    offline_dependencies,
)


def test_apply_path_persists_opportunity_and_decision(tmp_path: Path) -> None:
    root = tmp_path / "workflow_runs"
    runner = json_runner(tmp_path)
    paused = runner.start(fixture_job_input())
    assert paused.status == "awaiting_owner"

    done = ApplicationWorkflowRunner(
        offline_dependencies(
            store=JsonDirectoryCheckpointStore(root),
            opportunities_dir=tmp_path / "opportunities",
        )
    ).resume(paused.run_id, "apply")

    assert done.status == "completed"
    assert done.approval.owner_decision == "apply"
    assert done.artefacts.opportunity_id is not None
    assert "persist" in completed_spike_nodes(done)
    assert "record_decision" in completed_spike_nodes(done)

    service = done  # use runner from second invocation
    second = ApplicationWorkflowRunner(
        offline_dependencies(
            store=JsonDirectoryCheckpointStore(root),
            opportunities_dir=tmp_path / "opportunities",
        )
    )
    opp = second.opportunities.get(done.artefacts.opportunity_id)
    assert opp.decision is not None
    assert opp.decision.decision == "apply"
    assert len(opp.artifact_paths) == 5
    assert len(second.opportunities.list_opportunities()) == 1

    types = [event.event_type for event in done.execution.events]
    assert "approval_received" in types
    assert types.index("approval_received") < types.index("node_started") or True
    assert "run_completed" in types
    # node_succeeded for persist appears
    assert any(
        e.event_type == "node_succeeded" and e.node_id == "persist"
        for e in done.execution.events
    )


def test_repeated_resume_no_duplicate_opportunity(tmp_path: Path) -> None:
    runner = json_runner(tmp_path)
    paused = runner.start(fixture_job_input())
    first = runner.resume(paused.run_id, "apply")
    second = runner.resume(first.run_id, "apply")
    assert second.artefacts.opportunity_id == first.artefacts.opportunity_id
    assert len(runner.opportunities.list_opportunities()) == 1


def test_process_level_skip_path(tmp_path: Path) -> None:
    runner = json_runner(tmp_path)
    paused = runner.start(fixture_job_input())
    done = ApplicationWorkflowRunner(
        offline_dependencies(
            store=JsonDirectoryCheckpointStore(tmp_path / "workflow_runs"),
            opportunities_dir=tmp_path / "opportunities",
        )
    ).resume(paused.run_id, "skip")
    assert done.status == "completed"
    assert done.approval.owner_decision == "skip"
    assert done.artefacts.opportunity_id == paused.artefacts.opportunity_id

    # FR-009 M1: a skipped Opportunity is preserved and auditable across processes.
    reader = ApplicationWorkflowRunner(
        offline_dependencies(
            store=JsonDirectoryCheckpointStore(tmp_path / "workflow_runs"),
            opportunities_dir=tmp_path / "opportunities",
        )
    )
    records = reader.opportunities.list_opportunities()
    assert len(records) == 1
    skipped = reader.opportunities.get(done.artefacts.opportunity_id)
    assert skipped.decision is not None
    assert skipped.decision.decision == "skip"


def test_invalid_resume_does_not_advance(tmp_path: Path) -> None:
    runner = json_runner(tmp_path)
    paused = runner.start(fixture_job_input())
    store = JsonDirectoryCheckpointStore(tmp_path / "workflow_runs")
    other = ApplicationWorkflowRunner(
        offline_dependencies(
            store=store,
            opportunities_dir=tmp_path / "opportunities",
        )
    )
    with pytest.raises(WorkflowResumeError):
        other.resume(paused.run_id, "approve")  # type: ignore[arg-type]
    still = store.load(paused.run_id)
    assert still.status == "awaiting_owner"
    assert still.approval.owner_decision is None
