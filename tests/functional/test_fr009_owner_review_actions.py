"""Functional journeys for FR-009 M2 owner review actions."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from career_intelligence.opportunities import (
    OpportunityReviewService,
    OpportunityService,
)
from career_intelligence.opportunities.models import OpportunityReview
from career_intelligence.opportunities.yaml_store import YamlDirectoryOpportunityStore
from career_intelligence.review_queue import PINNED_REASON, ReviewQueueService
from tests.unit.opportunities.helpers import create_opportunity
from tests.unit.opportunity_comparison.helpers import ID_A, ID_B, ID_C, make_opportunity
from tests.unit.review_queue.helpers import STAMP as QSTAMP
from tests.unit.review_queue.helpers import queue_opportunity

STAMP = datetime(2026, 7, 30, 11, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)
UNTIL = date(2026, 8, 15)


def _services(
    tmp_path: Path,
) -> tuple[OpportunityService, OpportunityReviewService, ReviewQueueService]:
    opportunities = OpportunityService.from_path(tmp_path)
    return (
        opportunities,
        OpportunityReviewService(opportunities),
        ReviewQueueService(opportunities),
    )


def test_mark_reviewed_journey_keeps_record_awaiting_decision(tmp_path: Path) -> None:
    opportunities, review, queue = _services(tmp_path)
    _, opportunity, artefacts = create_opportunity(tmp_path)
    posting, analysis, assessment, match, strategy = artefacts

    updated = review.mark_reviewed(
        opportunity.opportunity_id, reviewed_at=STAMP, occurred_at=STAMP
    )
    assert updated.review.reviewed_at == STAMP
    assert updated.decision is None
    assert opportunity.opportunity_id in queue.list_awaiting_review(
        reference_date=REF
    ).opportunity_ids

    reloaded = opportunities.get(opportunity.opportunity_id)
    assert reloaded.artifact_paths == opportunity.artifact_paths
    for name, expected in (
        ("posting.json", posting),
        ("job_analysis.json", analysis),
        ("assessment.json", assessment),
        ("portfolio_match.json", match),
        ("strategy.json", strategy),
    ):
        path = tmp_path / "artifacts" / opportunity.opportunity_id / name
        assert path.is_file()
        assert path.stat().st_size > 0
        _ = expected


def test_pin_journey_raises_then_unpin_restores_m4_order(tmp_path: Path) -> None:
    store = YamlDirectoryOpportunityStore(tmp_path)
    strong = make_opportunity(
        ID_A,
        pursuit_posture="prioritise",
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

    opportunities = OpportunityService(store=store)
    review = OpportunityReviewService(opportunities)
    queue = ReviewQueueService(opportunities)

    before = queue.list_awaiting_review(reference_date=REF)
    assert before.opportunity_ids == [ID_A, ID_B]

    review.pin(ID_B, occurred_at=STAMP)
    pinned = queue.list_awaiting_review(reference_date=REF)
    assert pinned.opportunity_ids == [ID_B, ID_A]
    assert pinned.items[0].reasons[0] == PINNED_REASON
    assert opportunities.get(ID_B).strategy_summary == weak.strategy_summary

    review.unpin(ID_B, occurred_at=STAMP)
    restored = queue.list_awaiting_review(reference_date=REF)
    assert restored.opportunity_ids == [ID_A, ID_B]


def test_timed_defer_clear_and_expiry_journey(tmp_path: Path) -> None:
    opportunities, review, queue = _services(tmp_path)
    _, opportunity, _ = create_opportunity(tmp_path)
    oid = opportunity.opportunity_id

    review.defer_until(oid, UNTIL, reference_date=REF, occurred_at=STAMP)
    assert oid not in queue.list_awaiting_review(reference_date=REF).opportunity_ids
    assert oid not in queue.list_active_opportunities(reference_date=REF).opportunity_ids
    assert opportunities.get(oid).status == "assessed"

    assert oid in queue.list_active_opportunities(reference_date=UNTIL).opportunity_ids
    assert oid not in queue.list_awaiting_review(reference_date=UNTIL).opportunity_ids

    review.defer_until(oid, UNTIL, reference_date=REF, occurred_at=STAMP)
    review.clear_defer(oid, occurred_at=STAMP)
    cleared = opportunities.get(oid)
    assert cleared.decision is None
    assert cleared.review.defer_until is None
    assert oid in queue.list_awaiting_review(reference_date=REF).opportunity_ids


def test_archive_reopen_respects_remaining_decision_state(tmp_path: Path) -> None:
    opportunities, review, queue = _services(tmp_path)
    _, opportunity, _ = create_opportunity(tmp_path)
    oid = opportunity.opportunity_id

    review.archive(oid, archived_at=STAMP, occurred_at=STAMP)
    assert oid not in queue.list_awaiting_review(reference_date=REF).opportunity_ids
    assert oid not in queue.list_active_opportunities(reference_date=REF).opportunity_ids

    review.reopen(oid, occurred_at=STAMP)
    assert oid in queue.list_awaiting_review(reference_date=REF).opportunity_ids

    opportunities.record_decision(oid, "skip")
    review.archive(oid, archived_at=STAMP, occurred_at=STAMP)
    review.reopen(oid, occurred_at=STAMP)
    assert oid not in queue.list_active_opportunities(reference_date=REF).opportunity_ids
    skipped = next(
        item
        for item in queue.list_active_opportunities(reference_date=REF).excluded
        if item.opportunity_id == oid
    )
    assert skipped.exclusion_reasons == ("skipped",)


def test_mixed_state_projection_inclusion_and_pin_order(tmp_path: Path) -> None:
    records = [
        queue_opportunity(ID_A),
        queue_opportunity(ID_B, review=OpportunityReview(reviewed_at=QSTAMP)),
        queue_opportunity(
            ID_C,
            pursuit_posture="consider",
            review=OpportunityReview(pinned=True),
        ),
    ]
    store = YamlDirectoryOpportunityStore(tmp_path)
    for record in records:
        store.create_index_only(record)

    queue = ReviewQueueService(OpportunityService(store=store))
    awaiting = queue.list_awaiting_review(reference_date=REF)
    assert awaiting.opportunity_ids[0] == ID_C
    assert set(awaiting.opportunity_ids) == {ID_A, ID_B, ID_C}
