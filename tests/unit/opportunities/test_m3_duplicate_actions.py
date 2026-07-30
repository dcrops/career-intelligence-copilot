"""Unit tests for FR-009 M3 owner duplicate actions.

The central guarantee is non-destructive linking: after any sequence of duplicate
actions every discovered advertisement is still present and readable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from career_intelligence.duplicates import DuplicateDetectionService
from career_intelligence.opportunities import (
    DuplicateReviewService,
    OpportunityReviewService,
    OpportunityService,
)
from career_intelligence.opportunities.errors import (
    OpportunityNotFoundError,
    OpportunityTransitionError,
    OpportunityValidationError,
)
from career_intelligence.opportunity_comparison import OpportunityComparisonService
from career_intelligence.review_queue import ReviewQueueService
from tests.unit.duplicates.helpers import ID_1, ID_2, ID_3, ad, store_with

OCCURRED = datetime(2026, 7, 30, 11, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 31, 11, 0, 0, tzinfo=UTC)


def _services(
    tmp_path: Path, records: list | None = None
) -> tuple[OpportunityService, DuplicateReviewService]:
    opportunities = store_with(
        tmp_path,
        records
        if records is not None
        else [
            ad(ID_1, source_kind="seek", platform_job_id="12345"),
            ad(ID_2, source_kind="linkedin", platform_job_id="98765"),
        ],
    )
    return opportunities, DuplicateReviewService(opportunities)


def test_confirm_duplicate_links_without_deleting_either_record(
    tmp_path: Path,
) -> None:
    opportunities, duplicates = _services(tmp_path)
    updated = duplicates.confirm_duplicate(
        ID_2, ID_1, evidence=("identity_facets",), occurred_at=OCCURRED
    )

    assert updated.duplicate is not None
    assert updated.duplicate.duplicate_of == ID_1
    assert updated.duplicate.evidence == ("identity_facets",)
    assert {item.opportunity_id for item in opportunities.list_opportunities()} == {
        ID_1,
        ID_2,
    }
    # The canonical record is untouched by the link.
    assert opportunities.get(ID_1).duplicate is None


def test_confirm_duplicate_is_idempotent_and_preserves_confirmed_at(
    tmp_path: Path,
) -> None:
    opportunities, duplicates = _services(tmp_path)
    first = duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)
    second = duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=LATER)

    assert second.duplicate is not None
    assert first.duplicate is not None
    assert second.duplicate.confirmed_at == first.duplicate.confirmed_at
    assert len(second.review_actions) == 1


def test_confirm_duplicate_rejects_self_reference(tmp_path: Path) -> None:
    _, duplicates = _services(tmp_path)
    with pytest.raises(OpportunityValidationError):
        duplicates.confirm_duplicate(ID_1, ID_1, occurred_at=OCCURRED)


def test_confirm_duplicate_rejects_chains(tmp_path: Path) -> None:
    _, duplicates = _services(
        tmp_path,
        [
            ad(ID_1),
            ad(ID_2),
            ad(ID_3),
        ],
    )
    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)

    # ID_2 already points at ID_1, so it cannot become a duplicate of ID_3 too.
    with pytest.raises(OpportunityTransitionError):
        duplicates.confirm_duplicate(ID_2, ID_3, occurred_at=OCCURRED)
    # ID_3 cannot point at ID_2 either, which would create a two-hop chain.
    with pytest.raises(OpportunityTransitionError):
        duplicates.confirm_duplicate(ID_3, ID_2, occurred_at=OCCURRED)


def test_confirm_duplicate_rejects_repointing_an_existing_canonical(
    tmp_path: Path,
) -> None:
    _, duplicates = _services(tmp_path, [ad(ID_1), ad(ID_2), ad(ID_3)])
    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)

    with pytest.raises(OpportunityTransitionError):
        duplicates.confirm_duplicate(ID_1, ID_3, occurred_at=OCCURRED)


def test_confirm_duplicate_requires_existing_records(tmp_path: Path) -> None:
    _, duplicates = _services(tmp_path)
    with pytest.raises(OpportunityNotFoundError):
        duplicates.confirm_duplicate(ID_2, "opp_01ARZ3NDEKTSV4RRFFQ69G5FZZ")


def test_reject_duplicate_is_symmetric_and_idempotent(tmp_path: Path) -> None:
    opportunities, duplicates = _services(tmp_path)
    first, second = duplicates.reject_duplicate(
        ID_1, ID_2, note="different teams", occurred_at=OCCURRED
    )

    assert [item.other_opportunity_id for item in first.duplicate_rejections] == [ID_2]
    assert [item.other_opportunity_id for item in second.duplicate_rejections] == [ID_1]

    duplicates.reject_duplicate(ID_2, ID_1, occurred_at=LATER)
    assert len(opportunities.get(ID_1).duplicate_rejections) == 1
    assert opportunities.get(ID_1).duplicate_rejections[0].rejected_at == OCCURRED


def test_rejected_pair_disappears_from_detection(tmp_path: Path) -> None:
    opportunities, duplicates = _services(tmp_path)
    detection = DuplicateDetectionService(opportunities)
    assert len(detection.list_candidates().candidates) == 1

    duplicates.reject_duplicate(ID_1, ID_2, occurred_at=OCCURRED)
    assert detection.list_candidates().candidates == ()


def test_reject_duplicate_cannot_contradict_a_confirmed_link(tmp_path: Path) -> None:
    _, duplicates = _services(tmp_path)
    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)

    with pytest.raises(OpportunityTransitionError):
        duplicates.reject_duplicate(ID_1, ID_2, occurred_at=OCCURRED)


def test_confirm_duplicate_refuses_a_previously_rejected_pair(tmp_path: Path) -> None:
    _, duplicates = _services(tmp_path)
    duplicates.reject_duplicate(ID_1, ID_2, occurred_at=OCCURRED)

    with pytest.raises(OpportunityTransitionError):
        duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=LATER)


def test_reject_duplicate_rejects_self_reference(tmp_path: Path) -> None:
    _, duplicates = _services(tmp_path)
    with pytest.raises(OpportunityValidationError):
        duplicates.reject_duplicate(ID_1, ID_1)


def test_confirm_canonical_repoints_the_whole_group(tmp_path: Path) -> None:
    opportunities, duplicates = _services(
        tmp_path,
        [
            ad(ID_1),
            ad(ID_2, source_kind="seek", platform_job_id="12345"),
            ad(ID_3, source_kind="linkedin", platform_job_id="98765"),
        ],
    )
    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)
    duplicates.confirm_duplicate(ID_3, ID_1, occurred_at=OCCURRED)

    group = duplicates.confirm_canonical(ID_2, occurred_at=LATER)

    assert [record.opportunity_id for record in group] == [ID_2, ID_1, ID_3]
    assert opportunities.get(ID_2).duplicate is None
    assert opportunities.get(ID_1).duplicate is not None
    assert opportunities.get(ID_1).duplicate.duplicate_of == ID_2
    assert opportunities.get(ID_3).duplicate.duplicate_of == ID_2
    assert len(opportunities.list_opportunities()) == 3


def test_confirm_canonical_is_idempotent(tmp_path: Path) -> None:
    opportunities, duplicates = _services(tmp_path)
    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)
    before = opportunities.get(ID_2)

    duplicates.confirm_canonical(ID_1, occurred_at=LATER)
    after = opportunities.get(ID_2)

    assert after == before


def test_confirm_canonical_requires_a_confirmed_group(tmp_path: Path) -> None:
    _, duplicates = _services(tmp_path)
    with pytest.raises(OpportunityTransitionError):
        duplicates.confirm_canonical(ID_1, occurred_at=OCCURRED)


def test_duplicate_actions_preserve_unrelated_state(tmp_path: Path) -> None:
    opportunities, duplicates = _services(tmp_path)
    review = OpportunityReviewService(opportunities)
    review.mark_reviewed(ID_2, occurred_at=OCCURRED)
    opportunities.record_decision(ID_2, "apply", notes="strong role")
    before = opportunities.get(ID_2)

    after = duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=LATER)

    assert after.decision == before.decision
    assert after.status == before.status
    assert after.outcome == before.outcome
    assert after.strategy_summary == before.strategy_summary
    assert after.artifact_paths == before.artifact_paths
    assert after.identity == before.identity
    assert after.review == before.review


def test_duplicate_actions_append_audit_entries(tmp_path: Path) -> None:
    opportunities, duplicates = _services(tmp_path, [ad(ID_1), ad(ID_2), ad(ID_3)])
    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)
    duplicates.reject_duplicate(ID_1, ID_3, occurred_at=OCCURRED)
    duplicates.confirm_canonical(ID_2, occurred_at=LATER)

    actions = [entry.action for entry in opportunities.get(ID_2).review_actions]
    assert actions == ["confirm_duplicate", "confirm_canonical"]
    assert [entry.action for entry in opportunities.get(ID_3).review_actions] == [
        "reject_duplicate"
    ]
    assert opportunities.get(ID_1).review_actions[0].detail == f"not_duplicate_of={ID_3}"


def test_confirmed_duplicate_leaves_the_queue_but_canonical_stays(
    tmp_path: Path,
) -> None:
    opportunities, duplicates = _services(tmp_path)
    queue = ReviewQueueService(opportunities, comparison=OpportunityComparisonService())
    assert set(queue.list_awaiting_review().opportunity_ids) == {ID_1, ID_2}

    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)
    projection = queue.list_awaiting_review()

    assert projection.opportunity_ids == [ID_1]
    excluded = {
        item.opportunity_id: item.exclusion_reasons for item in projection.excluded
    }
    assert "confirmed_duplicate" in excluded[ID_2]


def test_duplicate_state_survives_reload(tmp_path: Path) -> None:
    opportunities, duplicates = _services(tmp_path)
    duplicates.confirm_duplicate(ID_2, ID_1, occurred_at=OCCURRED)

    reloaded = OpportunityService.from_path(tmp_path / "opportunities")
    record = reloaded.get(ID_2)

    assert record.duplicate is not None
    assert record.duplicate.duplicate_of == ID_1
    assert record.review_actions[0].action == "confirm_duplicate"
