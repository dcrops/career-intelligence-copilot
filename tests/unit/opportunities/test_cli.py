"""CLI tests for opportunity list/show (M1)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app

from .helpers import create_opportunity

runner = CliRunner()


def test_list_empty(tmp_path: Path) -> None:
    result = runner.invoke(app, ["opportunity", "list", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No opportunities persisted." in result.output


def test_list_and_show_populated(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(tmp_path)
    listed = runner.invoke(app, ["opportunity", "list", "--dir", str(tmp_path)])
    assert listed.exit_code == 0
    assert opportunity.opportunity_id in listed.output
    assert "prioritise" in listed.output or "platinum" in listed.output

    shown = runner.invoke(
        app,
        ["opportunity", "show", opportunity.opportunity_id, "--dir", str(tmp_path)],
    )
    assert shown.exit_code == 0
    assert opportunity.opportunity_id in shown.output
    assert "artifact_paths" in shown.output
    assert "strategy_summary" in shown.output


def test_list_yaml_output(tmp_path: Path) -> None:
    create_opportunity(tmp_path)
    result = runner.invoke(
        app, ["opportunity", "list", "--dir", str(tmp_path), "--yaml"]
    )
    assert result.exit_code == 0
    assert "opportunity_id:" in result.output


def test_show_missing_id(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["opportunity", "show", "opp_01ARZ3NDEKTSV4RRFFQ69G5FAV", "--dir", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "Opportunity not found" in result.output
