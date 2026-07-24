"""Tests for Opportunity CSV export (M3)."""

from __future__ import annotations

import csv
from pathlib import Path

from career_intelligence.opportunities import (
    EXPORT_COLUMNS,
    OpportunityCsvBridge,
    OpportunityCsvExporter,
    OpportunityService,
)

from .helpers import create_opportunity


def test_export_empty_store(tmp_path: Path) -> None:
    out = tmp_path / "empty.csv"
    path = OpportunityCsvExporter().export([], out)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert path.exists()
    assert list(csv.DictReader(path.open(encoding="utf-8-sig")).fieldnames) == list(
        EXPORT_COLUMNS
    )
    assert rows == []


def test_export_single_and_multiple_deterministic(tmp_path: Path) -> None:
    store = tmp_path / "opps"
    create_opportunity(store, company="Alpha Co", title="Role A")
    create_opportunity(store, company="Beta Co", title="Role B")
    service = OpportunityService.from_path(store)
    service.record_decision(service.list_opportunities()[0].opportunity_id, "apply")

    out1 = tmp_path / "a.csv"
    out2 = tmp_path / "b.csv"
    bridge = OpportunityCsvBridge.from_path(store)
    bridge.export_opportunities_csv(out1)
    bridge.export_opportunities_csv(out2)
    assert out1.read_text(encoding="utf-8-sig") == out2.read_text(encoding="utf-8-sig")

    with out1.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert list(rows[0].keys()) == list(EXPORT_COLUMNS)
    # Newest first by opportunity_id
    assert rows[0]["opportunity_id"] > rows[1]["opportunity_id"]


def test_export_notes_commas_quotes_unicode(tmp_path: Path) -> None:
    store = tmp_path / "opps"
    service, opportunity, _ = create_opportunity(store, company="ユニコード")
    service.record_decision(
        opportunity.opportunity_id,
        "apply",
        notes='Said "hello", then left\nnext line',
    )
    out = tmp_path / "notes.csv"
    OpportunityCsvBridge.from_path(store).export_opportunities_csv(out)
    with out.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["company"] == "ユニコード"
    assert 'Said "hello"' in rows[0]["decision_notes"]
    assert "next line" in rows[0]["decision_notes"]


def test_export_does_not_mutate_store(tmp_path: Path) -> None:
    store = tmp_path / "opps"
    service, opportunity, _ = create_opportunity(store)
    before = service.get(opportunity.opportunity_id).model_dump(mode="json")
    OpportunityCsvBridge.from_path(store).export_opportunities_csv(tmp_path / "x.csv")
    after = service.get(opportunity.opportunity_id).model_dump(mode="json")
    assert before == after


def test_export_missing_strategy_fields_empty(tmp_path: Path) -> None:
    # Legacy-shaped record with no strategy_summary
    from datetime import UTC, datetime

    from career_intelligence.opportunities.models import (
        LegacyImportProvenance,
        Opportunity,
        OpportunityIdentity,
        OwnerDecisionRecord,
    )
    from career_intelligence.opportunities.ulid import generate_ulid

    store = tmp_path / "opps"
    now = datetime.now(UTC)
    opp = Opportunity(
        identity=OpportunityIdentity(
            opportunity_id=f"opp_{generate_ulid()}",
            created_at=now,
            source_kind="import",
            company="Legacy Co",
            title="Legacy Role",
        ),
        status="submitted",
        decision=OwnerDecisionRecord(decision="apply", decided_at=now),
        strategy_summary=None,
        legacy_import=LegacyImportProvenance(
            source_file="x.csv",
            source_row_number=2,
            import_fingerprint="abc",
            imported_at=now,
        ),
        updated_at=now,
    )
    OpportunityService.from_path(store).create_from_legacy(opp)
    out = tmp_path / "legacy.csv"
    OpportunityCsvBridge.from_path(store).export_opportunities_csv(out)
    with out.open(encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["pursuit_posture"] == ""
    assert row["has_artifacts"] == "no"
    assert row["owner_decision"] == "apply"
