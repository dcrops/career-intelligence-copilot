"""Functional journeys for FR-009 M3 duplicate review.

Uses the real YAML store and real FR-002–FR-005 artefact snapshots so the
non-destructive guarantee is proven against files on disk, not mocks.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from career_intelligence.duplicates import DuplicateDetectionService
from career_intelligence.opportunities import (
    DuplicateReviewService,
    OpportunityService,
)
from career_intelligence.opportunities.errors import OpportunityTransitionError
from career_intelligence.opportunities.models import DuplicateRelation
from career_intelligence.review_queue import ReviewQueueService

SEEK_URL = "https://au.seek.com/job/93487188"
LINKEDIN_URL = "https://www.linkedin.com/jobs/view/4123456789"
STAMP = datetime(2026, 7, 30, 11, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 31, 11, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)


def _seed(tmp_path: Path) -> tuple[OpportunityService, list[str]]:
    """One vacancy advertised on two platforms, plus one unrelated vacancy."""
    from tests.unit.opportunities.helpers import create_opportunity

    ids: list[str] = []
    service, seek, _ = create_opportunity(tmp_path, source_url=SEEK_URL)
    ids.append(seek.opportunity_id)
    _, linkedin, _ = create_opportunity(tmp_path, source_url=LINKEDIN_URL)
    ids.append(linkedin.opportunity_id)
    _, unrelated, _ = create_opportunity(
        tmp_path,
        source_url="https://www.indeed.com/viewjob?jk=abcdef1234567890",
        title="Warehouse Manager",
        company="Beta Logistics",
        raw_text=(
            "Senior AI Engineer. Python required. Hybrid Melbourne. "
            "Separate advertisement body for an unrelated vacancy."
        ),
    )
    ids.append(unrelated.opportunity_id)
    return service, ids


def _services(
    opportunities: OpportunityService,
) -> tuple[DuplicateDetectionService, DuplicateReviewService, ReviewQueueService]:
    return (
        DuplicateDetectionService(opportunities),
        DuplicateReviewService(opportunities),
        ReviewQueueService(opportunities),
    )


def test_cross_platform_duplicate_is_suggested_and_owner_confirms(
    tmp_path: Path,
) -> None:
    opportunities, (seek_id, linkedin_id, unrelated_id) = _seed(tmp_path)
    detection, duplicates, queue = _services(opportunities)

    report = detection.list_candidates(generated_at=STAMP)
    assert report.pairs == (tuple(sorted((seek_id, linkedin_id))),)
    candidate = report.candidates[0]
    assert candidate.confidence == "probable"
    assert "company" in candidate.comparison.matching
    assert "platform" in candidate.comparison.differing
    assert unrelated_id not in candidate.pair

    duplicates.confirm_duplicate(linkedin_id, seek_id, occurred_at=STAMP)

    # Linked, not merged: both advertisements and both artefact sets survive.
    assert len(opportunities.list_opportunities()) == 3
    for opportunity_id in (seek_id, linkedin_id):
        for name in ("posting.json", "job_analysis.json", "strategy.json"):
            assert (tmp_path / "artifacts" / opportunity_id / name).is_file()

    groups = detection.list_groups()
    assert len(groups) == 1
    assert groups[0].canonical_opportunity_id == seek_id
    assert groups[0].member_opportunity_ids == (linkedin_id,)

    projection = queue.list_awaiting_review(reference_date=REF)
    assert linkedin_id not in projection.opportunity_ids
    assert seek_id in projection.opportunity_ids
    assert detection.list_candidates(generated_at=LATER).candidates == ()


def test_rejected_suggestion_never_reappears(tmp_path: Path) -> None:
    opportunities, (seek_id, linkedin_id, _) = _seed(tmp_path)
    detection, duplicates, queue = _services(opportunities)

    assert len(detection.list_candidates(generated_at=STAMP).candidates) == 1
    duplicates.reject_duplicate(
        seek_id, linkedin_id, note="different team and seniority", occurred_at=STAMP
    )

    for _ in range(3):
        assert detection.list_candidates(generated_at=LATER).candidates == ()

    # Both records remain independently reviewable.
    projection = queue.list_awaiting_review(reference_date=REF)
    assert seek_id in projection.opportunity_ids
    assert linkedin_id in projection.opportunity_ids
    with pytest.raises(OpportunityTransitionError):
        duplicates.confirm_duplicate(linkedin_id, seek_id, occurred_at=LATER)


def test_unresolved_candidate_stays_reviewable_until_the_owner_acts(
    tmp_path: Path,
) -> None:
    opportunities, (seek_id, linkedin_id, _) = _seed(tmp_path)
    detection, _, queue = _services(opportunities)

    for _ in range(3):
        report = detection.list_candidates(generated_at=STAMP)
        assert report.pairs == (tuple(sorted((seek_id, linkedin_id))),)
        assert report.owner_confirmation_required is True

    # Unresolved suggestions never remove a record from the decision queue.
    projection = queue.list_awaiting_review(reference_date=REF)
    assert {seek_id, linkedin_id} <= set(projection.opportunity_ids)


def test_owner_confirms_a_different_canonical_without_losing_records(
    tmp_path: Path,
) -> None:
    opportunities, (seek_id, linkedin_id, _) = _seed(tmp_path)
    detection, duplicates, _ = _services(opportunities)
    duplicates.confirm_duplicate(seek_id, linkedin_id, occurred_at=STAMP)

    recommendation = detection.recommend_canonical(seek_id)
    assert recommendation.current_canonical_opportunity_id == linkedin_id
    assert recommendation.recommended_opportunity_id == seek_id
    assert recommendation.matches_current is False
    assert recommendation.owner_confirmation_required is True

    group = duplicates.confirm_canonical(
        recommendation.recommended_opportunity_id, occurred_at=LATER
    )

    assert [record.opportunity_id for record in group] == [seek_id, linkedin_id]
    assert opportunities.get(seek_id).duplicate is None
    assert opportunities.get(linkedin_id).duplicate.duplicate_of == seek_id
    assert len(opportunities.list_opportunities()) == 3
    assert detection.recommend_canonical(seek_id).matches_current is True


def test_interrupted_canonical_change_converges_on_replay(tmp_path: Path) -> None:
    """A crash mid-repoint leaves a partial star; re-running the action repairs it."""
    opportunities, (seek_id, linkedin_id, third_id) = _seed(tmp_path)
    detection, duplicates, _ = _services(opportunities)
    duplicates.confirm_duplicate(seek_id, linkedin_id, occurred_at=STAMP)
    duplicates.confirm_duplicate(third_id, linkedin_id, occurred_at=STAMP)

    # Simulate the process dying after the first member was re-pointed at seek_id
    # but before the chosen canonical's own relation was cleared.
    partial = opportunities.get(third_id)
    opportunities.replace(
        partial.model_copy(
            update={
                "duplicate": DuplicateRelation(
                    duplicate_of=seek_id,
                    confirmed_at=STAMP,
                    evidence=("owner_judgment",),
                )
            },
            deep=True,
        )
    )
    assert opportunities.get(seek_id).duplicate is not None

    duplicates.confirm_canonical(seek_id, occurred_at=LATER)

    assert opportunities.get(seek_id).duplicate is None
    assert opportunities.get(linkedin_id).duplicate.duplicate_of == seek_id
    assert opportunities.get(third_id).duplicate.duplicate_of == seek_id
    groups = detection.list_groups()
    assert len(groups) == 1
    assert groups[0].member_opportunity_ids == tuple(sorted((linkedin_id, third_id)))
    assert len(opportunities.list_opportunities()) == 3


def test_repeated_duplicate_actions_are_idempotent(tmp_path: Path) -> None:
    opportunities, (seek_id, linkedin_id, third_id) = _seed(tmp_path)
    detection, duplicates, _ = _services(opportunities)

    duplicates.confirm_duplicate(linkedin_id, seek_id, occurred_at=STAMP)
    duplicates.confirm_duplicate(linkedin_id, seek_id, occurred_at=LATER)
    duplicates.reject_duplicate(seek_id, third_id, occurred_at=STAMP)
    duplicates.reject_duplicate(third_id, seek_id, occurred_at=LATER)
    duplicates.confirm_canonical(seek_id, occurred_at=STAMP)
    duplicates.confirm_canonical(seek_id, occurred_at=LATER)

    member = opportunities.get(linkedin_id)
    canonical = opportunities.get(seek_id)
    assert member.duplicate.confirmed_at == STAMP
    assert [entry.action for entry in member.review_actions] == ["confirm_duplicate"]
    assert [entry.action for entry in canonical.review_actions] == ["reject_duplicate"]
    assert len(canonical.duplicate_rejections) == 1
    assert canonical.duplicate_rejections[0].rejected_at == STAMP
    assert len(detection.list_groups()) == 1


def test_duplicate_state_and_artefacts_survive_a_fresh_service(tmp_path: Path) -> None:
    opportunities, (seek_id, linkedin_id, _) = _seed(tmp_path)
    _, duplicates, _ = _services(opportunities)
    duplicates.confirm_duplicate(linkedin_id, seek_id, occurred_at=STAMP)

    reloaded = OpportunityService.from_path(tmp_path)
    detection = DuplicateDetectionService(reloaded)
    member = reloaded.get(linkedin_id)

    assert member.duplicate.duplicate_of == seek_id
    assert member.artifact_paths
    assert detection.list_groups()[0].canonical_opportunity_id == seek_id
    assert detection.list_candidates(generated_at=LATER).candidates == ()
