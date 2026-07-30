"""Functional acceptance: FR-009 M1 pre-review persistence + review projection.

Uses the real JSON checkpoint store and the real YAML opportunity store so the
durability claims are proved on disk rather than through mocks.
"""

from __future__ import annotations

from pathlib import Path

from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_data_engineer,
)
from career_intelligence.opportunities import OpportunityService
from career_intelligence.orchestration import (
    ApplicationWorkflowRunner,
    JsonDirectoryCheckpointStore,
)
from career_intelligence.review_queue import ReviewQueueService
from tests.unit.orchestration.m1_helpers import (
    fixture_job_input,
    fixture_job_input_for,
    offline_dependencies,
    rewind_before,
)


def _runs(tmp_path: Path) -> Path:
    return tmp_path / "workflow_runs"


def _opps(tmp_path: Path) -> Path:
    return tmp_path / "opportunities"


def _fresh_runner(tmp_path: Path) -> ApplicationWorkflowRunner:
    """A runner with its own process-like instances over the same directories."""
    return ApplicationWorkflowRunner(
        offline_dependencies(
            store=JsonDirectoryCheckpointStore(_runs(tmp_path)),
            opportunities_dir=_opps(tmp_path),
        )
    )


def _queue(tmp_path: Path) -> ReviewQueueService:
    return ReviewQueueService(OpportunityService.from_path(_opps(tmp_path)))


def test_apply_journey_updates_the_record_created_before_review(
    tmp_path: Path,
) -> None:
    paused = _fresh_runner(tmp_path).start(fixture_job_input())
    opportunity_id = paused.artefacts.opportunity_id
    assert paused.status == "awaiting_owner"
    assert opportunity_id is not None
    assert _queue(tmp_path).list_awaiting_review().opportunity_ids == [opportunity_id]

    done = _fresh_runner(tmp_path).resume(paused.run_id, "apply")
    assert done.status == "completed"
    assert done.artefacts.opportunity_id == opportunity_id

    service = OpportunityService.from_path(_opps(tmp_path))
    assert len(service.list_opportunities()) == 1
    assert service.get(opportunity_id).decision.decision == "apply"  # type: ignore[union-attr]

    queue = _queue(tmp_path)
    assert queue.list_awaiting_review().opportunity_ids == []
    assert queue.list_active_opportunities().opportunity_ids == [opportunity_id]


def test_skip_journey_keeps_the_record_but_leaves_the_default_queue(
    tmp_path: Path,
) -> None:
    paused = _fresh_runner(tmp_path).start(fixture_job_input())
    opportunity_id = paused.artefacts.opportunity_id
    done = _fresh_runner(tmp_path).resume(paused.run_id, "skip")

    assert done.status == "completed"
    service = OpportunityService.from_path(_opps(tmp_path))
    assert len(service.list_opportunities()) == 1
    assert service.get(opportunity_id).decision.decision == "skip"  # type: ignore[arg-type,union-attr]

    queue = _queue(tmp_path).list_active_opportunities()
    assert queue.opportunity_ids == []
    assert [verdict.exclusion_reasons for verdict in queue.excluded] == [("skipped",)]


def test_defer_journey_keeps_the_record_but_leaves_the_default_queue(
    tmp_path: Path,
) -> None:
    paused = _fresh_runner(tmp_path).start(fixture_job_input())
    opportunity_id = paused.artefacts.opportunity_id
    done = _fresh_runner(tmp_path).resume(paused.run_id, "defer")

    assert done.status == "completed"
    record = OpportunityService.from_path(_opps(tmp_path)).get(opportunity_id)  # type: ignore[arg-type]
    assert record.decision.decision == "defer"  # type: ignore[union-attr]
    # FR-009 M1 does not write pipeline status or a defer date.
    assert record.status == "assessed"
    assert record.review.defer_until is None

    queue = _queue(tmp_path).list_active_opportunities()
    assert queue.opportunity_ids == []
    assert [verdict.exclusion_reasons for verdict in queue.excluded] == [("deferred",)]


def test_rerunning_the_workflow_after_a_lost_checkpoint_creates_no_duplicate(
    tmp_path: Path,
) -> None:
    paused = _fresh_runner(tmp_path).start(fixture_job_input())
    opportunity_id = paused.artefacts.opportunity_id

    # Crash window: the Opportunity is on disk, the completion record is not.
    store = JsonDirectoryCheckpointStore(_runs(tmp_path))
    store.save(rewind_before(store.load(paused.run_id), nodes={"persist", "owner_review"}))

    resumed = _fresh_runner(tmp_path).continue_run(paused.run_id)
    assert resumed.status == "awaiting_owner"
    assert resumed.artefacts.opportunity_id == opportunity_id

    done = _fresh_runner(tmp_path).resume(paused.run_id, "apply")
    assert done.status == "completed"
    records = OpportunityService.from_path(_opps(tmp_path)).list_opportunities()
    assert [record.opportunity_id for record in records] == [opportunity_id]


def test_several_analysed_jobs_queue_in_deterministic_review_order(
    tmp_path: Path,
) -> None:
    postings = [
        posting_data_engineer(),
        posting_ai_engineer(),
        posting_applied_ai_engineer(),
    ]
    for posting in postings:
        state = _fresh_runner(tmp_path).start(fixture_job_input_for(posting))
        assert state.status == "awaiting_owner"

    queue = _queue(tmp_path).list_awaiting_review()
    assert queue.included_count == 3
    assert queue.excluded_count == 0
    assert [item.rank for item in queue.items] == [1, 2, 3]
    # Ordered by the M4 fit hierarchy, not by acquisition order.
    assert [item.pursuit_posture for item in queue.items] == [
        "pursue",
        "consider",
        "do_not_prioritise",
    ]
    assert [item.title for item in queue.items] == [
        "Applied AI Engineer",
        "Senior AI Engineer",
        "Data Engineer",
    ]
    assert all(item.reasons for item in queue.items)
    assert _queue(tmp_path).list_awaiting_review().opportunity_ids == queue.opportunity_ids
