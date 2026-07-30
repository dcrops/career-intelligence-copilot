"""Functional journeys for FR-009 M4 opportunity recommendations."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from career_intelligence.opportunities import (
    DuplicateReviewService,
    OpportunityReviewService,
    OpportunityService,
)
from career_intelligence.recommendations import OpportunityRecommendationService
from career_intelligence.review_queue import ReviewQueueService
from tests.unit.opportunities.helpers import create_opportunity

STAMP = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)


def _seed_three(tmp_path: Path) -> tuple[OpportunityService, list[str]]:
    service, first, _ = create_opportunity(
        tmp_path,
        source_url="https://au.seek.com/job/11111111",
        title="Senior AI Engineer",
        company="Alpha AI",
        raw_text="Senior AI Engineer. Python required. Hybrid Melbourne. Alpha.",
    )
    _, second, _ = create_opportunity(
        tmp_path,
        source_url="https://www.linkedin.com/jobs/view/22222222",
        title="Senior AI Engineer",
        company="Alpha AI",
        raw_text="Senior AI Engineer. Python required. Hybrid Melbourne. Alpha.",
    )
    _, third, _ = create_opportunity(
        tmp_path,
        source_url="https://au.seek.com/job/33333333",
        title="Data Engineer",
        company="Beta Data",
        raw_text="Data Engineer. SQL and Spark. Onsite Sydney. Distinct body.",
    )
    return service, [first.opportunity_id, second.opportunity_id, third.opportunity_id]


def test_recommendation_order_is_deterministic_and_explained(tmp_path: Path) -> None:
    opportunities, ids = _seed_three(tmp_path)
    recommendations = OpportunityRecommendationService(opportunities)

    first = recommendations.recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    second = recommendations.recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )

    assert first.opportunity_ids == second.opportunity_ids
    assert set(first.opportunity_ids) == set(ids)
    assert first.owner_review_required is True
    top = first.items[0]
    assert top.ranking_reasons
    assert top.recommended_next_action == "record_owner_decision"
    assert top.positives or top.negatives or top.missing


def test_recommendations_respect_duplicates_and_pins(tmp_path: Path) -> None:
    opportunities, (a, b, c) = _seed_three(tmp_path)
    duplicates = DuplicateReviewService(opportunities)
    review = OpportunityReviewService(opportunities)
    recommendations = OpportunityRecommendationService(opportunities)
    queue = ReviewQueueService(opportunities)

    duplicates.confirm_duplicate(b, a, occurred_at=STAMP)
    # Pin the weaker/later record among remaining eligible ones.
    before = recommendations.recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert b not in before.opportunity_ids
    assert a in before.opportunity_ids
    canonical = next(item for item in before.items if item.opportunity_id == a)
    assert canonical.duplicate_group_size == 2

    review.pin(c, occurred_at=STAMP)
    after = recommendations.recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert after.opportunity_ids[0] == c
    assert after.items[0].pinned is True
    assert queue.list_awaiting_review(reference_date=REF).opportunity_ids[0] == c


def test_apply_decision_changes_next_action_not_ranking_inputs(
    tmp_path: Path,
) -> None:
    opportunities, (a, *_rest) = _seed_three(tmp_path)
    recommendations = OpportunityRecommendationService(opportunities)
    before = opportunities.get(a)

    opportunities.record_decision(a, "apply")
    report = recommendations.recommend_active(reference_date=REF, generated_at=STAMP)
    item = next(entry for entry in report.items if entry.opportunity_id == a)

    assert item.recommended_next_action == "prepare_application_package"
    assert "awaiting owner action" not in " | ".join(item.ranking_reasons).lower()
    assert "ready for package preparation" in " | ".join(item.ranking_reasons)
    # Ranking inputs untouched by the recommendation query / decision recording path.
    reloaded = opportunities.get(a)
    assert reloaded.strategy_summary == before.strategy_summary
    assert reloaded.artifact_paths == before.artifact_paths


def test_recommendation_query_is_idempotent_across_services(tmp_path: Path) -> None:
    opportunities, _ids = _seed_three(tmp_path)
    path = tmp_path
    report_a = OpportunityRecommendationService(opportunities).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    reloaded = OpportunityService.from_path(path)
    report_b = OpportunityRecommendationService(reloaded).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert report_a.opportunity_ids == report_b.opportunity_ids
    assert [item.model_dump() for item in report_a.items] == [
        item.model_dump() for item in report_b.items
    ]
