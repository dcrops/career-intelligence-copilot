"""Tests for legacy tracker CSV import (M3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.opportunities import (
    OpportunityCsvBridge,
    OpportunityService,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "opportunities"


def test_dry_run_creates_nothing(tmp_path: Path) -> None:
    store = tmp_path / "opps"
    bridge = OpportunityCsvBridge.from_path(store)
    report = bridge.import_legacy_opportunities_csv(
        FIXTURES / "legacy_tracker_valid.csv",
        dry_run=True,
        report_path=tmp_path / "report.json",
    )
    assert report.dry_run is True
    assert report.rows_read == 2
    assert report.rows_imported == 0
    assert all(item.result == "would_import" for item in report.row_results)
    assert OpportunityService.from_path(store).list_opportunities() == []
    assert (tmp_path / "report.json").is_file()


def test_import_valid_rows_and_reload(tmp_path: Path) -> None:
    store = tmp_path / "opps"
    bridge = OpportunityCsvBridge.from_path(store)
    report = bridge.import_legacy_opportunities_csv(
        FIXTURES / "legacy_tracker_valid.csv"
    )
    assert report.rows_imported == 2
    assert report.rows_failed == 0
    service = OpportunityService.from_path(store)
    items = service.list_opportunities()
    assert len(items) == 2
    by_company = {item.identity.company: item for item in items}
    h2o = by_company["H2O.ai"]
    assert h2o.decision is not None and h2o.decision.decision == "apply"
    assert h2o.status == "submitted"
    assert h2o.outcome is not None and h2o.outcome.outcome == "pending"
    assert h2o.strategy_summary is None
    assert h2o.artifact_paths == {}
    assert h2o.legacy_import is not None
    assert h2o.identity.source_kind == "linkedin"
    assert (store / "artifacts").exists() is False or list(
        (store / "artifacts").iterdir()
    ) == []


def test_mixed_rows_row_atomic(tmp_path: Path) -> None:
    store = tmp_path / "opps"
    report = OpportunityCsvBridge.from_path(store).import_legacy_opportunities_csv(
        FIXTURES / "legacy_tracker_mixed.csv"
    )
    assert report.rows_imported == 1
    assert report.rows_failed == 3
    assert len(OpportunityService.from_path(store).list_opportunities()) == 1


def test_repeated_import_skips_duplicates(tmp_path: Path) -> None:
    store = tmp_path / "opps"
    bridge = OpportunityCsvBridge.from_path(store)
    first = bridge.import_legacy_opportunities_csv(FIXTURES / "legacy_tracker_valid.csv")
    second = bridge.import_legacy_opportunities_csv(FIXTURES / "legacy_tracker_valid.csv")
    assert first.rows_imported == 2
    assert second.rows_imported == 0
    assert second.rows_skipped == 2
    assert all(item.result == "skipped_duplicate" for item in second.row_results)
    assert len(OpportunityService.from_path(store).list_opportunities()) == 2


def test_markdown_tracker_import(tmp_path: Path) -> None:
    """Import the live markdown-style applications/application_tracker.csv shape."""
    source = (
        Path(__file__).resolve().parents[3]
        / "applications"
        / "application_tracker.csv"
    )
    if not source.is_file():
        pytest.skip("application_tracker.csv not present")
    store = tmp_path / "opps"
    report = OpportunityCsvBridge.from_path(store).import_legacy_opportunities_csv(
        source,
        dry_run=True,
    )
    assert report.rows_read >= 2
    assert report.rows_failed == 0
    assert report.rows_imported == 0
