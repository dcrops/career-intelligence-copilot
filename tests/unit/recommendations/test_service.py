"""Unit tests for FR-009 M4 recommendation explanations and ordering."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from career_intelligence.opportunities import (
    DuplicateReviewService,
    OpportunityReviewService,
    OpportunityService,
)
from career_intelligence.opportunities.models import OpportunityReview
from career_intelligence.opportunities.yaml_store import YamlDirectoryOpportunityStore
from career_intelligence.recommendations import OpportunityRecommendationService
from tests.unit.opportunity_comparison.helpers import (
    ID_A,
    ID_B,
    ID_C,
    make_opportunity,
)
from tests.unit.review_queue.helpers import queue_opportunity

STAMP = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)


def _store(tmp_path: Path, records: list) -> OpportunityService:
    store = YamlDirectoryOpportunityStore(tmp_path / "opportunities")
    for record in records:
        store.create_index_only(record)
    return OpportunityService(store=store)


def _service(tmp_path: Path, records: list) -> OpportunityRecommendationService:
    return OpportunityRecommendationService(_store(tmp_path, records))


def test_recommendations_follow_calibrated_quality_order(tmp_path: Path) -> None:
    records = [
        make_opportunity(
            ID_A,
            pursuit_posture="consider",
            application_tier="platinum",
            practical_value="volume_obligation",
        ),
        make_opportunity(
            ID_B,
            pursuit_posture="consider",
            application_tier="bronze",
            practical_value="career_priority",
        ),
        make_opportunity(ID_C, pursuit_posture="prioritise", practical_value="career_priority"),
    ]
    report = _service(tmp_path, records).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert report.opportunity_ids == [ID_C, ID_B, ID_A]
    assert report.items[0].priority_band == "immediate"
    assert report.items[1].practical_value == "career_priority"
    assert report.items[2].practical_value == "volume_obligation"


def test_tie_break_and_replay_are_stable(tmp_path: Path) -> None:
    records = [
        make_opportunity(ID_B, pursuit_posture="pursue"),
        make_opportunity(ID_A, pursuit_posture="pursue"),
    ]
    service = _service(tmp_path, records)
    first = service.recommend_awaiting_review(reference_date=REF, generated_at=STAMP)
    second = service.recommend_awaiting_review(reference_date=REF, generated_at=STAMP)
    assert first.opportunity_ids == second.opportunity_ids == [ID_A, ID_B]
    assert first.items == second.items


def test_missing_salary_and_location_do_not_raise_priority(tmp_path: Path) -> None:
    """Absent optional fields must not invent confidence or reorder by fantasy signals."""
    rich = make_opportunity(ID_A, pursuit_posture="pursue")
    sparse = make_opportunity(
        ID_B,
        pursuit_posture="pursue",
        company="Sparse Co",
        title="AI Engineer",
    )
    # Strip location by rebuilding through queue helper defaults — make_opportunity has no
    # location_text; both lack it. Verify explanations report missing location without
    # changing relative order vs posture/value.
    report = _service(tmp_path, [sparse, rich]).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert report.opportunity_ids == [ID_A, ID_B]
    for item in report.items:
        assert "Location text missing from Opportunity identity" in item.missing


def test_urgency_from_follow_up_not_invented_deadlines(tmp_path: Path) -> None:
    due = make_opportunity(ID_A, follow_up_date=date(2026, 7, 29), decision="apply")
    upcoming = make_opportunity(ID_B, follow_up_date=date(2026, 8, 3), decision="apply")
    plain = make_opportunity(ID_C, decision="apply")
    report = _service(tmp_path, [plain, upcoming, due]).recommend_active(
        reference_date=REF, generated_at=STAMP
    )
    by_id = {item.opportunity_id: item for item in report.items}
    assert by_id[ID_A].urgency == "due"
    assert by_id[ID_B].urgency == "upcoming"
    assert by_id[ID_C].urgency == "none"
    assert by_id[ID_C].recommended_next_action == "prepare_application_package"


def test_next_action_for_undecided_and_expired_defer(tmp_path: Path) -> None:
    undecided = make_opportunity(ID_A)
    deferred = queue_opportunity(
        ID_B,
        decision="defer",
        review=OpportunityReview(defer_until=date(2026, 7, 30)),
    )
    report = _service(tmp_path, [undecided, deferred]).recommend_active(
        reference_date=REF, generated_at=STAMP
    )
    by_id = {item.opportunity_id: item for item in report.items}
    assert by_id[ID_A].recommended_next_action == "record_owner_decision"
    assert by_id[ID_B].recommended_next_action == "re_review_expired_defer"


def test_pin_override_preserved_and_explained(tmp_path: Path) -> None:
    strong = make_opportunity(ID_A, pursuit_posture="prioritise")
    weak = queue_opportunity(
        ID_B,
        pursuit_posture="consider",
        application_tier="silver",
        review=OpportunityReview(pinned=True),
    )
    report = _service(tmp_path, [strong, weak]).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert report.opportunity_ids == [ID_B, ID_A]
    assert report.items[0].pinned is True
    assert "Pinned by owner for presentation prominence" in report.items[0].positives


def test_confirmed_duplicate_excluded_canonical_annotated(tmp_path: Path) -> None:
    opportunities = _store(
        tmp_path,
        [
            make_opportunity(ID_A, pursuit_posture="prioritise"),
            make_opportunity(ID_B, pursuit_posture="prioritise"),
            make_opportunity(ID_C, pursuit_posture="consider"),
        ],
    )
    duplicates = DuplicateReviewService(opportunities)
    duplicates.confirm_duplicate(ID_B, ID_A, occurred_at=STAMP)

    report = OpportunityRecommendationService(opportunities).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert ID_B not in report.opportunity_ids
    assert ID_A in report.opportunity_ids
    canonical = next(item for item in report.items if item.opportunity_id == ID_A)
    assert canonical.duplicate_group_size == 2


def test_recommendations_are_read_only(tmp_path: Path) -> None:
    opportunities = _store(tmp_path, [make_opportunity(ID_A), make_opportunity(ID_B)])
    index = tmp_path / "opportunities" / "index.yaml"
    before = index.read_text(encoding="utf-8")
    OpportunityRecommendationService(opportunities).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert index.read_text(encoding="utf-8") == before


def test_legacy_incomplete_record_ranks_last_with_missing(tmp_path: Path) -> None:
    complete = make_opportunity(ID_B, pursuit_posture="do_not_prioritise")
    incomplete = make_opportunity(ID_A, incomplete=True)
    report = _service(tmp_path, [incomplete, complete]).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert report.opportunity_ids == [ID_B, ID_A]
    assert "Strategy summary absent" in report.items[1].missing[0]


def test_review_actions_unchanged_by_recommendation_queries(tmp_path: Path) -> None:
    opportunities = _store(tmp_path, [make_opportunity(ID_A)])
    review = OpportunityReviewService(opportunities)
    review.mark_reviewed(ID_A, occurred_at=STAMP)
    before = opportunities.get(ID_A)
    OpportunityRecommendationService(opportunities).recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    assert opportunities.get(ID_A) == before
