"""Unit tests for FR-009 M3 canonical recommendation and group projection."""

from __future__ import annotations

from datetime import UTC, datetime

from career_intelligence.duplicates import (
    build_groups,
    group_for,
    metadata_completeness,
    recommend_canonical,
)
from tests.unit.duplicates.helpers import ID_1, ID_2, ID_3, ad


def test_records_with_artefacts_are_preferred_as_canonical() -> None:
    with_evidence = ad(ID_2, with_artifacts=True)
    without_evidence = ad(ID_1, source_kind="seek", platform_job_id="12345")

    recommendation = recommend_canonical([without_evidence, with_evidence])

    assert recommendation.recommended_opportunity_id == ID_2
    assert "Has full analysis and strategy artefact snapshots" in recommendation.reasons


def test_recruiter_reposts_rank_below_direct_advertisers() -> None:
    recruiter = ad(ID_1, source_kind="recruiter", platform_job_id="r-1")
    direct = ad(ID_2, source_kind="seek", platform_job_id="12345")

    recommendation = recommend_canonical([recruiter, direct])

    assert recommendation.recommended_opportunity_id == ID_2


def test_metadata_completeness_breaks_platform_ties() -> None:
    sparse = ad(ID_1, source_kind="seek", platform_job_id=None, location_text=None)
    complete = ad(
        ID_2,
        source_kind="seek",
        platform_job_id="12345",
        canonical_url="https://www.seek.com.au/job/12345",
        source_url="https://www.seek.com.au/job/12345?ref=search",
        content_fingerprint="c" * 64,
    )

    assert metadata_completeness(complete) > metadata_completeness(sparse)
    assert recommend_canonical([complete, sparse]).recommended_opportunity_id == ID_2


def test_earliest_discovery_wins_when_all_else_is_equal() -> None:
    later = ad(ID_1, created_at=datetime(2026, 7, 25, tzinfo=UTC))
    earlier = ad(ID_2, created_at=datetime(2026, 7, 20, tzinfo=UTC))

    assert recommend_canonical([later, earlier]).recommended_opportunity_id == ID_2


def test_recommendation_is_order_independent_and_advisory() -> None:
    first = ad(ID_1, duplicate_of=ID_2)
    second = ad(ID_2, source_kind="seek", platform_job_id="12345")

    forwards = recommend_canonical([first, second])
    backwards = recommend_canonical([second, first])

    assert forwards == backwards
    assert forwards.owner_confirmation_required is True
    assert forwards.current_canonical_opportunity_id == ID_2
    assert forwards.matches_current is True


def test_groups_are_derived_from_confirmed_links_only() -> None:
    canonical = ad(ID_1)
    member = ad(ID_2, duplicate_of=ID_1)
    unrelated = ad(ID_3, company="Beta Industries", title="Warehouse Manager")

    groups = build_groups([unrelated, member, canonical])

    assert len(groups) == 1
    assert groups[0].canonical_opportunity_id == ID_1
    assert groups[0].member_opportunity_ids == (ID_2,)
    assert groups[0].size == 2
    assert group_for(ID_3, [unrelated, member, canonical]) is None
    assert group_for(ID_2, [unrelated, member, canonical]) == groups[0]
