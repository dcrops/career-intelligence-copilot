"""Unit tests for FR-009 M1 pre-review Opportunity persistence (ADR-004).

The Opportunity becomes durable after Application Strategy and before the owner
review interrupt, and apply / skip / defer all update that same record.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from career_intelligence.orchestration import (
    FailureInjection,
    InMemoryCheckpointStore,
    WorkflowResumeError,
    WorkflowState,
    completed_spike_nodes,
)
from career_intelligence.orchestration.side_effect_nodes import RecordDecisionNode
from tests.unit.orchestration.m1_helpers import (
    fixture_job_input,
    offline_runner,
    rewind_before,
)


def test_opportunity_is_durable_before_the_owner_review_interrupt(
    tmp_path: Path,
) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())

    assert paused.status == "awaiting_owner"
    assert paused.artefacts.opportunity_id is not None
    stored = runner.opportunities.list_opportunities()
    assert len(stored) == 1
    record = stored[0]
    assert record.opportunity_id == paused.artefacts.opportunity_id
    assert record.decision is None
    assert record.status == "assessed"
    assert len(record.artifact_paths) == 5
    # Default review metadata: never reviewed, not pinned, not archived, not deferred.
    assert record.review.reviewed_at is None
    assert record.review.pinned is False
    assert record.review.defer_until is None
    assert record.review.archived_at is None
    assert record.duplicate is None


def test_checkpoint_carries_the_id_but_not_the_opportunity_record(
    tmp_path: Path,
) -> None:
    store = InMemoryCheckpointStore()
    runner = offline_runner(store=store, opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())

    reloaded = store.load(paused.run_id)
    assert reloaded.artefacts.opportunity_id == paused.artefacts.opportunity_id

    payload = json.dumps(reloaded.model_dump(mode="json"))
    # Checkpoints stay recovery data: the id locates the record, it is not a copy.
    assert "strategy_summary" not in payload
    assert "artifact_paths" not in payload


def test_persist_failure_pauses_before_the_interrupt_and_creates_nothing(
    tmp_path: Path,
) -> None:
    store = InMemoryCheckpointStore()
    opps = tmp_path / "opps"
    failing = offline_runner(
        store=store,
        opportunities_dir=opps,
        failure_injection=FailureInjection(
            node_id="persist", fail_count=1, kind="recoverable"
        ),
    )
    paused = failing.start(fixture_job_input())

    assert paused.status == "running"
    assert paused.control.last_error is not None
    assert "owner_review" not in completed_spike_nodes(paused)
    assert paused.approval.pending_kind is None
    assert failing.opportunities.list_opportunities() == []
    planned = paused.artefacts.opportunity_id
    assert planned is not None  # planned id survived the failure

    recovered = offline_runner(store=store, opportunities_dir=opps)
    resumed = recovered.continue_run(paused.run_id)
    assert resumed.status == "awaiting_owner"
    assert resumed.artefacts.opportunity_id == planned
    stored = recovered.opportunities.list_opportunities()
    assert [item.opportunity_id for item in stored] == [planned]


def test_replayed_persist_node_reuses_the_existing_record(tmp_path: Path) -> None:
    store = InMemoryCheckpointStore()
    runner = offline_runner(store=store, opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    created = runner.opportunities.get(paused.artefacts.opportunity_id)  # type: ignore[arg-type]

    # Crash window: the record was written but its completion never checkpointed.
    store.save(rewind_before(paused, nodes={"persist", "owner_review"}))
    replayed = runner.continue_run(paused.run_id)

    assert replayed.status == "awaiting_owner"
    assert replayed.artefacts.opportunity_id == paused.artefacts.opportunity_id
    stored = runner.opportunities.list_opportunities()
    assert len(stored) == 1
    assert stored[0].identity.created_at == created.identity.created_at
    assert stored[0].artifact_paths == created.artifact_paths


def test_crash_between_checkpoint_and_interrupt_resumes_into_owner_review(
    tmp_path: Path,
) -> None:
    store = InMemoryCheckpointStore()
    runner = offline_runner(store=store, opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())

    # Persist is durable; only the interrupt was lost.
    store.save(rewind_before(paused, nodes={"owner_review"}))
    resumed = runner.continue_run(paused.run_id)

    assert resumed.status == "awaiting_owner"
    assert resumed.approval.owner_decision is None
    assert len(runner.opportunities.list_opportunities()) == 1


@pytest.mark.parametrize("decision", ["apply", "skip", "defer"])
def test_every_decision_updates_the_same_persisted_record(
    tmp_path: Path, decision: str
) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / decision)
    paused = runner.start(fixture_job_input())
    pre_review_id = paused.artefacts.opportunity_id
    done = runner.resume(paused.run_id, decision)  # type: ignore[arg-type]

    assert done.status == "completed"
    assert done.artefacts.opportunity_id == pre_review_id
    stored = runner.opportunities.list_opportunities()
    assert len(stored) == 1
    record = stored[0]
    assert record.decision is not None
    assert record.decision.decision == decision
    assert record.decision.notes == f"workflow_run_id={done.run_id}"
    # Review metadata and pipeline status are not written by the workflow.
    assert record.status == "assessed"
    assert record.review.reviewed_at is None


def test_decision_update_failure_prevents_false_completion(tmp_path: Path) -> None:
    store = InMemoryCheckpointStore()
    runner = offline_runner(store=store, opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())

    real_record = runner.opportunities.record_decision
    calls = {"n": 0}

    def flaky(opportunity_id, decision, *, notes=None):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated decision write failure")
        return real_record(opportunity_id, decision, notes=notes)

    runner.opportunities.record_decision = flaky  # type: ignore[method-assign]
    stalled = runner.resume(paused.run_id, "skip")

    assert stalled.status == "running"
    assert stalled.control.last_error is not None
    assert "record_decision" not in completed_spike_nodes(stalled)
    assert runner.opportunities.get(stalled.artefacts.opportunity_id).decision is None  # type: ignore[arg-type]

    runner.opportunities.record_decision = real_record  # type: ignore[method-assign]
    done = runner.resume(stalled.run_id, "skip")
    assert done.status == "completed"
    assert len(runner.opportunities.list_opportunities()) == 1
    assert runner.opportunities.get(done.artefacts.opportunity_id).decision.decision == "skip"  # type: ignore[arg-type,union-attr]


def test_a_recorded_decision_is_not_silently_overwritten(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    applied = runner.resume(paused.run_id, "apply")

    with pytest.raises(WorkflowResumeError):
        runner.resume(applied.run_id, "skip")

    # A rewound run that tries to record a different decision fails closed.
    conflicting = WorkflowState.model_validate(
        rewind_before(applied, nodes={"record_decision"})
        .model_copy(
            update={
                "approval": applied.approval.model_copy(update={"owner_decision": "skip"})
            }
        )
        .model_dump(mode="python")
    )
    outcome = RecordDecisionNode(runner.opportunities).execute(conflicting)
    assert outcome.failure is not None
    assert "conflicting owner decision" in outcome.failure.message
    assert runner.opportunities.get(applied.artefacts.opportunity_id).decision.decision == "apply"  # type: ignore[arg-type,union-attr]


def test_repeating_the_same_decision_is_idempotent(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    first = runner.resume(paused.run_id, "defer")
    second = runner.resume(first.run_id, "defer")

    assert second.status == "completed"
    assert second.artefacts.opportunity_id == first.artefacts.opportunity_id
    assert len(runner.opportunities.list_opportunities()) == 1
