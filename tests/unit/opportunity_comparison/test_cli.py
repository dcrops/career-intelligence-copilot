"""Unit tests for opportunity compare CLI (M4)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.opportunities import OpportunityService
from tests.unit.opportunities.helpers import create_opportunity

runner = CliRunner()


def test_compare_empty(tmp_path: Path) -> None:
    OpportunityService.from_path(tmp_path)
    result = runner.invoke(app, ["opportunity", "compare", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No open opportunities" in result.output


def test_compare_lists_ranked_reasons(tmp_path: Path) -> None:
    create_opportunity(tmp_path, company="Alpha Co", title="AI Engineer")
    result = runner.invoke(app, ["opportunity", "compare", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Open opportunities ranked: 1" in result.output
    assert "Owner review required" in result.output
    assert "Pursuit posture:" in result.output
    assert "fit_strength=" in result.output


def test_compare_yaml_output(tmp_path: Path) -> None:
    create_opportunity(tmp_path)
    result = runner.invoke(
        app, ["opportunity", "compare", "--dir", str(tmp_path), "--yaml"]
    )
    assert result.exit_code == 0
    assert "open_count:" in result.output
    assert "owner_review_required: true" in result.output
    assert "reasons:" in result.output


def test_compare_excludes_skipped(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    service.record_decision(opportunity.opportunity_id, "skip")
    result = runner.invoke(app, ["opportunity", "compare", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Open opportunities ranked: 0" in result.output
    assert "excluded 1" in result.output
