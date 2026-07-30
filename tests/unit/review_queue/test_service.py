"""Unit tests for the FR-009 M1 derived review-queue projection."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunities.models import Opportunity, OpportunityReview
from career_intelligence.opportunities.yaml_store import YamlDirectoryOpportunityStore
from career_intelligence.opportunity_comparison import OpportunityComparisonService
from career_intelligence.review_queue import ReviewQueueService
from tests.unit.opportunity_comparison.helpers import (
    ID_A,
    ID_B,
    ID_C,
    ID_D,
    ID_E,
    ID_F,
)
from tests.unit.review_queue.helpers import REFERENCE_DATE, STAMP, queue_opportunity

# One index row written before FR-009 M0 existed: no review key at all.
LEGACY_ROW_WITHOUT_REVIEW_KEYS = {
    "identity": {
        "opportunity_id": "opp_01ARZ3NDEKTSV4RRFFQ69G5F00",
        "created_at": "2026-07-01T00:00:00Z",
        "source_kind": "manual",
        "company": "Legacy Co",
        "title": "AI Engineer",
    },
    "status": "assessed",
    "decision": {"decision": "apply", "decided_at": "2026-07-02T00:00:00Z"},
    "strategy_summary": {
        "pursuit_posture": "consider",
        "application_tier": "silver",
        "practical_value": "acceptable_opportunity",
        "technical_fit": "mixed",
        "commercial_fit": "mixed",
        "portfolio_fit": "moderate",
    },
    "artifact_paths": {},
    "updated_at": "2026-07-02T00:00:00Z",
}


def _store(tmp_path: Path, records: list[Opportunity]) -> YamlDirectoryOpportunityStore:
    store = YamlDirectoryOpportunityStore(tmp_path / "opportunities")
    for record in records:
        store.create_index_only(record)
    return store


def _queue_service(store: YamlDirectoryOpportunityStore) -> ReviewQueueService:
    return ReviewQueueService(OpportunityService(store=store))


def _mixed_records() -> list[Opportunity]:
    return [
        queue_opportunity(ID_A),  # pre-review, undecided
        queue_opportunity(ID_B, decision="apply"),
        queue_opportunity(ID_C, decision="skip"),
        queue_opportunity(ID_D, decision="defer"),
        queue_opportunity(
            ID_E, review=OpportunityReview(archived_at=STAMP), pursuit_posture="pursue"
        ),
        queue_opportunity(ID_F, duplicate_of=ID_A, pursuit_posture="pursue"),
    ]


def test_awaiting_review_holds_only_undecided_records(tmp_path: Path) -> None:
    service = _queue_service(_store(tmp_path, _mixed_records()))
    queue = service.list_awaiting_review(reference_date=REFERENCE_DATE)
    assert queue.scope == "awaiting_review"
    assert queue.opportunity_ids == [ID_A]
    assert queue.reference_date == REFERENCE_DATE


def test_active_queue_keeps_applied_records_and_explains_every_exclusion(
    tmp_path: Path,
) -> None:
    service = _queue_service(_store(tmp_path, _mixed_records()))
    queue = service.list_active_opportunities(reference_date=REFERENCE_DATE)

    assert set(queue.opportunity_ids) == {ID_A, ID_B}
    reasons = {
        verdict.opportunity_id: verdict.exclusion_reasons for verdict in queue.excluded
    }
    assert reasons == {
        ID_C: ("skipped",),
        ID_D: ("deferred",),
        ID_E: ("archived",),
        ID_F: ("confirmed_duplicate",),
    }
    assert queue.included_count == 2
    assert queue.excluded_count == 4
    assert [verdict.opportunity_id for verdict in queue.excluded] == sorted(reasons)


def test_ordering_matches_the_frozen_m4_baseline(tmp_path: Path) -> None:
    records = [
        queue_opportunity(ID_A, pursuit_posture="consider", application_tier="silver"),
        queue_opportunity(ID_B, pursuit_posture="prioritise"),
        queue_opportunity(ID_C, pursuit_posture="pursue", application_tier="gold"),
    ]
    service = _queue_service(_store(tmp_path, records))
    queue = service.list_awaiting_review(reference_date=REFERENCE_DATE)

    baseline = OpportunityComparisonService().compare_open(records)
    assert queue.opportunity_ids == [item.opportunity_id for item in baseline.items]
    assert queue.opportunity_ids == [ID_B, ID_C, ID_A]
    assert [item.rank for item in queue.items] == [1, 2, 3]
    assert all(item.reasons for item in queue.items)


def test_equal_signals_fall_back_to_stable_id_order(tmp_path: Path) -> None:
    records = [queue_opportunity(ID_C), queue_opportunity(ID_A), queue_opportunity(ID_B)]
    service = _queue_service(_store(tmp_path, records))
    first = service.list_awaiting_review(reference_date=REFERENCE_DATE)
    second = service.list_awaiting_review(reference_date=REFERENCE_DATE)
    assert first.opportunity_ids == [ID_A, ID_B, ID_C]
    assert first.opportunity_ids == second.opportunity_ids


def test_reference_date_decides_whether_a_deferred_record_returns(
    tmp_path: Path,
) -> None:
    deferred = queue_opportunity(
        ID_A,
        decision="defer",
        review=OpportunityReview(defer_until=date(2026, 8, 15)),
    )
    service = _queue_service(_store(tmp_path, [deferred]))
    assert service.list_active_opportunities(
        reference_date=date(2026, 8, 1)
    ).opportunity_ids == []
    assert service.list_active_opportunities(
        reference_date=date(2026, 8, 20)
    ).opportunity_ids == [ID_A]


def test_records_written_before_review_metadata_still_project(tmp_path: Path) -> None:
    store = _store(tmp_path, [queue_opportunity(ID_A)])
    raw = yaml.safe_load(store.index_path.read_text(encoding="utf-8"))
    raw["opportunities"].append(LEGACY_ROW_WITHOUT_REVIEW_KEYS)
    store.index_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    assert "review" not in LEGACY_ROW_WITHOUT_REVIEW_KEYS

    service = _queue_service(store)
    active = service.list_active_opportunities(reference_date=REFERENCE_DATE)
    assert set(active.opportunity_ids) == {
        ID_A,
        LEGACY_ROW_WITHOUT_REVIEW_KEYS["identity"]["opportunity_id"],  # type: ignore[index]
    }
    # The legacy record already has an apply decision, so it is not awaiting one.
    assert service.list_awaiting_review(
        reference_date=REFERENCE_DATE
    ).opportunity_ids == [ID_A]


def test_querying_the_queue_never_writes_to_the_store(tmp_path: Path) -> None:
    store = _store(tmp_path, _mixed_records())
    before = store.index_path.read_bytes()
    service = _queue_service(store)
    service.list_awaiting_review(reference_date=REFERENCE_DATE)
    service.list_active_opportunities(reference_date=REFERENCE_DATE)
    assert store.index_path.read_bytes() == before


def test_empty_store_yields_an_empty_queue(tmp_path: Path) -> None:
    service = _queue_service(YamlDirectoryOpportunityStore(tmp_path / "empty"))
    queue = service.list_awaiting_review(reference_date=REFERENCE_DATE)
    assert queue.items == []
    assert queue.excluded == []
