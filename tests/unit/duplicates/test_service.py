"""Unit tests for the FR-009 M3 read-only duplicate detection service."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from career_intelligence.duplicates import DuplicateDetectionService
from career_intelligence.opportunities import OpportunityService
from tests.unit.duplicates.helpers import ID_1, ID_2, ID_3, ad, store_with

GENERATED_AT = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

# An index row written before FR-009 M3 existed: no duplicate_rejections key at all.
LEGACY_ROW = {
    "identity": {
        "opportunity_id": "opp_01ARZ3NDEKTSV4RRFFQ69G5F00",
        "created_at": "2026-07-01T00:00:00Z",
        "source_kind": "manual",
        "company": "Acme Pty Ltd",
        "title": "AI Engineer",
    },
    "status": "assessed",
    "artifact_paths": {},
    "updated_at": "2026-07-02T00:00:00Z",
}


def _service(opportunities: OpportunityService) -> DuplicateDetectionService:
    return DuplicateDetectionService(opportunities)


def test_report_surfaces_unresolved_candidates_only(tmp_path: Path) -> None:
    opportunities = store_with(
        tmp_path,
        [
            ad(ID_1, source_kind="seek", platform_job_id="12345"),
            ad(ID_2, source_kind="linkedin", platform_job_id="98765"),
            ad(ID_3, company="Beta Industries", title="Warehouse Manager"),
        ],
    )
    report = _service(opportunities).list_candidates(generated_at=GENERATED_AT)

    assert report.generated_at == GENERATED_AT
    assert report.owner_confirmation_required is True
    assert report.pairs == ((ID_1, ID_2),)


def test_candidates_for_filters_to_one_record(tmp_path: Path) -> None:
    opportunities = store_with(
        tmp_path,
        [ad(ID_1), ad(ID_2), ad(ID_3, company="Beta Industries", title="Cook")],
    )
    service = _service(opportunities)

    assert service.candidates_for(ID_3) == ()
    assert len(service.candidates_for(ID_1)) == 1


def test_detection_is_read_only(tmp_path: Path) -> None:
    opportunities = store_with(
        tmp_path, [ad(ID_1), ad(ID_2)]
    )
    index = tmp_path / "opportunities" / "index.yaml"
    before = index.read_text(encoding="utf-8")

    service = _service(opportunities)
    service.list_candidates(generated_at=GENERATED_AT)
    service.list_groups()

    assert index.read_text(encoding="utf-8") == before


def test_groups_and_canonical_recommendation_come_from_the_store(
    tmp_path: Path,
) -> None:
    opportunities = store_with(
        tmp_path,
        [
            ad(ID_1, source_kind="manual"),
            ad(ID_2, source_kind="seek", platform_job_id="12345", duplicate_of=ID_1),
        ],
    )
    service = _service(opportunities)

    groups = service.list_groups()
    assert groups[0].canonical_opportunity_id == ID_1
    assert service.group_for(ID_2) == groups[0]

    recommendation = service.recommend_canonical(ID_2)
    assert recommendation.current_canonical_opportunity_id == ID_1
    # The SEEK advert carries a platform job id, so it is the better canonical.
    assert recommendation.recommended_opportunity_id == ID_2
    assert recommendation.matches_current is False


def test_recommendation_for_ungrouped_record_returns_itself(tmp_path: Path) -> None:
    opportunities = store_with(tmp_path, [ad(ID_1)])
    recommendation = _service(opportunities).recommend_canonical(ID_1)

    assert recommendation.recommended_opportunity_id == ID_1
    assert recommendation.group_opportunity_ids == (ID_1,)


def test_records_written_before_m3_remain_detectable(tmp_path: Path) -> None:
    root = tmp_path / "opportunities"
    root.mkdir(parents=True)
    (root / "index.yaml").write_text(
        yaml.safe_dump({"schema_version": "1", "opportunities": [LEGACY_ROW]}),
        encoding="utf-8",
    )
    opportunities = OpportunityService.from_path(root)
    legacy = opportunities.list_opportunities()[0]

    assert legacy.duplicate_rejections == ()
    report = _service(opportunities).list_candidates(generated_at=GENERATED_AT)
    assert report.candidates == ()
