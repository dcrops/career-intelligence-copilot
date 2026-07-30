"""Unit tests for FR-009 M2 owner review actions."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import yaml

from career_intelligence.opportunities import (
    OpportunityReviewService,
    OpportunityService,
    OpportunityTransitionError,
    OpportunityValidationError,
)
from career_intelligence.opportunities.yaml_store import YamlDirectoryOpportunityStore
from career_intelligence.review_queue import PINNED_REASON, ReviewQueueService

from .helpers import create_opportunity

STAMP = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)


def _review(tmp_path: Path) -> tuple[OpportunityService, OpportunityReviewService, str]:
    service, opportunity, _ = create_opportunity(tmp_path)
    return service, OpportunityReviewService(service), opportunity.opportunity_id


def test_mark_reviewed_sets_timestamp_without_creating_a_decision(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    updated = review.mark_reviewed(opportunity_id, reviewed_at=STAMP, occurred_at=STAMP)

    assert updated.review.reviewed_at == STAMP
    assert updated.decision is None
    assert updated.status == "assessed"
    assert len(updated.review_actions) == 1
    assert updated.review_actions[0].action == "mark_reviewed"
    assert opportunities.get(opportunity_id).review.reviewed_at == STAMP


def test_repeated_mark_reviewed_preserves_original_timestamp(tmp_path: Path) -> None:
    _, review, opportunity_id = _review(tmp_path)
    first = review.mark_reviewed(opportunity_id, reviewed_at=STAMP, occurred_at=STAMP)
    second = review.mark_reviewed(opportunity_id, reviewed_at=LATER, occurred_at=LATER)

    assert second.review.reviewed_at == STAMP
    assert second.opportunity_id == first.opportunity_id
    assert len(second.review_actions) == 1


def test_pin_and_unpin_are_reversible(tmp_path: Path) -> None:
    _, review, opportunity_id = _review(tmp_path)
    pinned = review.pin(opportunity_id, occurred_at=STAMP)
    assert pinned.review.pinned is True
    assert pinned.review_actions[-1].action == "pin"

    again = review.pin(opportunity_id, occurred_at=LATER)
    assert again.review.pinned is True
    assert len(again.review_actions) == 1

    unpinned = review.unpin(opportunity_id, occurred_at=LATER)
    assert unpinned.review.pinned is False
    assert unpinned.review_actions[-1].action == "unpin"

    noop = review.unpin(opportunity_id, occurred_at=LATER)
    assert noop.review.pinned is False
    assert len(noop.review_actions) == 2


def test_pin_on_archived_record_is_rejected(tmp_path: Path) -> None:
    _, review, opportunity_id = _review(tmp_path)
    review.archive(opportunity_id, archived_at=STAMP, occurred_at=STAMP)
    with pytest.raises(OpportunityTransitionError, match="archived"):
        review.pin(opportunity_id, occurred_at=LATER)


def test_archive_clears_pin_and_preserves_original_timestamp(tmp_path: Path) -> None:
    _, review, opportunity_id = _review(tmp_path)
    review.pin(opportunity_id, occurred_at=STAMP)
    archived = review.archive(opportunity_id, archived_at=STAMP, occurred_at=STAMP)

    assert archived.review.archived_at == STAMP
    assert archived.review.pinned is False
    assert archived.review_actions[-1].action == "archive"
    assert archived.review_actions[-1].detail == "cleared pin on archive"

    again = review.archive(opportunity_id, archived_at=LATER, occurred_at=LATER)
    assert again.review.archived_at == STAMP
    assert sum(1 for entry in again.review_actions if entry.action == "archive") == 1


def test_reopen_clears_archive_only(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    opportunities.record_decision(opportunity_id, "skip")
    review.mark_reviewed(opportunity_id, reviewed_at=STAMP, occurred_at=STAMP)
    review.archive(opportunity_id, archived_at=STAMP, occurred_at=STAMP)

    reopened = review.reopen(opportunity_id, occurred_at=LATER)
    assert reopened.review.archived_at is None
    assert reopened.decision is not None and reopened.decision.decision == "skip"
    assert reopened.review.reviewed_at == STAMP
    assert reopened.status == "assessed"

    noop = review.reopen(opportunity_id, occurred_at=LATER)
    assert noop.review.archived_at is None
    assert sum(1 for entry in noop.review_actions if entry.action == "reopen") == 1


def test_defer_until_rejects_past_dates_and_accepts_same_day(tmp_path: Path) -> None:
    _, review, opportunity_id = _review(tmp_path)
    with pytest.raises(OpportunityValidationError):
        review.defer_until(
            opportunity_id,
            date(2026, 7, 29),
            reference_date=REF,
            occurred_at=STAMP,
        )

    same_day = review.defer_until(
        opportunity_id,
        REF,
        reference_date=REF,
        occurred_at=STAMP,
    )
    assert same_day.review.defer_until == REF
    assert same_day.decision is not None and same_day.decision.decision == "defer"


def test_timed_defer_and_expiry_against_reference_date(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    until = date(2026, 8, 15)
    deferred = review.defer_until(
        opportunity_id, until, reference_date=REF, occurred_at=STAMP
    )
    assert deferred.review.defer_until == until
    assert deferred.status == "assessed"

    queue = ReviewQueueService(opportunities)
    before = queue.list_awaiting_review(reference_date=date(2026, 8, 14))
    on_day = queue.list_awaiting_review(reference_date=until)
    assert opportunity_id not in before.opportunity_ids
    # Expired defer still has decision=defer, so awaiting_review excludes as decided.
    assert opportunity_id not in on_day.opportunity_ids
    active = queue.list_active_opportunities(reference_date=until)
    assert opportunity_id in active.opportunity_ids


def test_clear_defer_restores_undecided_state(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    review.defer_until(
        opportunity_id, date(2026, 8, 15), reference_date=REF, occurred_at=STAMP
    )
    cleared = review.clear_defer(opportunity_id, occurred_at=LATER)

    assert cleared.review.defer_until is None
    assert cleared.decision is None
    assert cleared.review_actions[-1].action == "clear_defer"

    queue = ReviewQueueService(opportunities)
    assert opportunity_id in queue.list_awaiting_review(reference_date=REF).opportunity_ids

    noop = review.clear_defer(opportunity_id, occurred_at=LATER)
    assert sum(1 for entry in noop.review_actions if entry.action == "clear_defer") == 1


def test_defer_until_does_not_overwrite_apply_or_skip(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    opportunities.record_decision(opportunity_id, "apply")
    with pytest.raises(OpportunityTransitionError, match="apply"):
        review.defer_until(
            opportunity_id, date(2026, 8, 15), reference_date=REF, occurred_at=STAMP
        )


def test_actions_preserve_unrelated_aggregate_fields(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    before = opportunities.get(opportunity_id)
    opportunities.record_decision(opportunity_id, "apply", notes="pursue carefully")
    with_decision = opportunities.get(opportunity_id)

    review.mark_reviewed(opportunity_id, reviewed_at=STAMP, occurred_at=STAMP)
    review.pin(opportunity_id, occurred_at=STAMP)
    review.unpin(opportunity_id, occurred_at=STAMP)
    after = opportunities.get(opportunity_id)

    assert after.decision is not None and after.decision.decision == "apply"
    assert after.decision.notes == "pursue carefully"
    assert after.status == with_decision.status == "assessed"
    assert after.outcome == before.outcome
    assert after.strategy_summary == before.strategy_summary
    assert after.artifact_paths == before.artifact_paths
    assert after.identity == before.identity
    assert after.duplicate == before.duplicate
    assert after.legacy_import == before.legacy_import


def test_actions_never_create_a_second_opportunity(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    review.mark_reviewed(opportunity_id, reviewed_at=STAMP, occurred_at=STAMP)
    review.pin(opportunity_id, occurred_at=STAMP)
    review.archive(opportunity_id, archived_at=STAMP, occurred_at=STAMP)
    review.reopen(opportunity_id, occurred_at=LATER)
    assert [item.opportunity_id for item in opportunities.list_opportunities()] == [
        opportunity_id
    ]


def test_old_records_without_review_actions_still_load(tmp_path: Path) -> None:
    root = tmp_path / "opportunities"
    root.mkdir()
    (root / "artifacts").mkdir()
    index = {
        "schema_version": "1",
        "opportunities": [
            {
                "identity": {
                    "opportunity_id": "opp_01KY8RFAH81M9V30ZVH9TM09T5",
                    "created_at": "2026-07-24T00:30:15.080566Z",
                    "source_kind": "manual",
                    "company": "Example",
                    "title": "AI Engineer",
                },
                "status": "assessed",
                "decision": None,
                "strategy_summary": {
                    "pursuit_posture": "consider",
                    "application_tier": "silver",
                    "practical_value": "acceptable_opportunity",
                    "technical_fit": "mixed",
                    "commercial_fit": "mixed",
                    "portfolio_fit": "strong",
                },
                "artifact_paths": {},
                "updated_at": "2026-07-24T00:50:25.667178Z",
            }
        ],
    }
    (root / "index.yaml").write_text(yaml.safe_dump(index), encoding="utf-8")
    service = OpportunityService.from_path(root)
    record = service.get("opp_01KY8RFAH81M9V30ZVH9TM09T5")
    assert record.review_actions == ()
    assert record.review.pinned is False

    review = OpportunityReviewService(service)
    updated = review.pin(record.opportunity_id, occurred_at=STAMP)
    assert updated.review.pinned is True
    assert len(updated.review_actions) == 1


def test_review_actions_survive_round_trip(tmp_path: Path) -> None:
    opportunities, review, opportunity_id = _review(tmp_path)
    review.mark_reviewed(opportunity_id, reviewed_at=STAMP, occurred_at=STAMP)
    review.pin(opportunity_id, occurred_at=STAMP)
    reloaded = OpportunityService.from_path(tmp_path).get(opportunity_id)
    assert [entry.action for entry in reloaded.review_actions] == [
        "mark_reviewed",
        "pin",
    ]


def test_pin_raises_weak_fit_above_strong_fit_in_projection(tmp_path: Path) -> None:
    strong, weak = _two_ranked_opportunities(tmp_path)
    review = OpportunityReviewService(OpportunityService.from_path(tmp_path))
    queue_before = ReviewQueueService(OpportunityService.from_path(tmp_path))
    before = queue_before.list_awaiting_review(reference_date=REF)
    assert before.opportunity_ids[0] == strong

    review.pin(weak, occurred_at=STAMP)
    after = ReviewQueueService(
        OpportunityService.from_path(tmp_path)
    ).list_awaiting_review(reference_date=REF)
    assert after.opportunity_ids[0] == weak
    assert after.items[0].reasons[0] == PINNED_REASON
    # Fit values on the ranked item are unchanged presentation metadata from M4.
    weak_item = next(item for item in after.items if item.opportunity_id == weak)
    strong_item = next(item for item in after.items if item.opportunity_id == strong)
    assert weak_item.fit_strength < strong_item.fit_strength

    review.unpin(weak, occurred_at=LATER)
    restored = ReviewQueueService(
        OpportunityService.from_path(tmp_path)
    ).list_awaiting_review(reference_date=REF)
    assert restored.opportunity_ids[0] == strong


def _two_ranked_opportunities(tmp_path: Path) -> tuple[str, str]:
    from tests.unit.opportunity_comparison.helpers import ID_A, ID_B, make_opportunity

    store = YamlDirectoryOpportunityStore(tmp_path)
    strong = make_opportunity(
        ID_A,
        pursuit_posture="prioritise",
        application_tier="platinum",
        technical_fit="strong",
        commercial_fit="strong",
        portfolio_fit="strong",
    )
    weak = make_opportunity(
        ID_B,
        pursuit_posture="consider",
        application_tier="silver",
        technical_fit="mixed",
        commercial_fit="mixed",
        portfolio_fit="moderate",
    )
    store.create_index_only(strong)
    store.create_index_only(weak)
    return ID_A, ID_B
