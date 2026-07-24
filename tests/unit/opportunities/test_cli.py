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


def test_decide_and_outcome_commands(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(tmp_path)
    oid = opportunity.opportunity_id

    decided = runner.invoke(
        app,
        ["opportunity", "decide", oid, "apply", "--dir", str(tmp_path), "--notes", "Go"],
    )
    assert decided.exit_code == 0
    assert "apply" in decided.output
    assert "status unchanged" in decided.output

    submitted = runner.invoke(
        app,
        [
            "opportunity",
            "outcome",
            oid,
            "--dir",
            str(tmp_path),
            "--status",
            "submitted",
            "--outcome",
            "pending",
        ],
    )
    assert submitted.exit_code == 0
    assert "submitted" in submitted.output

    interviewing = runner.invoke(
        app,
        [
            "opportunity",
            "outcome",
            oid,
            "--dir",
            str(tmp_path),
            "--status",
            "interviewing",
            "--interview-stage",
            "recruiter",
        ],
    )
    assert interviewing.exit_code == 0

    shown = runner.invoke(app, ["opportunity", "show", oid, "--dir", str(tmp_path)])
    assert shown.exit_code == 0
    assert "decision: apply" in shown.output or "decision:\n  apply" in shown.output
    assert "interviewing" in shown.output
    assert "pending" in shown.output


def test_decide_invalid_value(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(tmp_path)
    result = runner.invoke(
        app,
        ["opportunity", "decide", opportunity.opportunity_id, "maybe", "--dir", str(tmp_path)],
    )
    assert result.exit_code == 1


def test_outcome_invalid_transition(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(tmp_path)
    result = runner.invoke(
        app,
        [
            "opportunity",
            "outcome",
            opportunity.opportunity_id,
            "--dir",
            str(tmp_path),
            "--status",
            "interviewing",
        ],
    )
    assert result.exit_code == 1
    assert "Invalid status transition" in result.output or "transition" in result.output


def test_export_csv_command(tmp_path: Path) -> None:
    create_opportunity(tmp_path / "opps")
    out = tmp_path / "export.csv"
    result = runner.invoke(
        app,
        [
            "opportunity",
            "export-csv",
            "--dir",
            str(tmp_path / "opps"),
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0
    assert out.is_file()
    assert "Exported 1" in result.output


def test_import_legacy_csv_dry_run_and_import(tmp_path: Path) -> None:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "opportunities"
        / "legacy_tracker_valid.csv"
    )
    store = tmp_path / "opps"
    dry = runner.invoke(
        app,
        [
            "opportunity",
            "import-legacy-csv",
            str(fixture),
            "--dir",
            str(store),
            "--dry-run",
            "--report",
            str(tmp_path / "dry.json"),
        ],
    )
    assert dry.exit_code == 0
    assert "DRY RUN" in dry.output
    assert "would_import" in dry.output

    real = runner.invoke(
        app,
        ["opportunity", "import-legacy-csv", str(fixture), "--dir", str(store)],
    )
    assert real.exit_code == 0
    assert "rows_imported: 2" in real.output

    again = runner.invoke(
        app,
        ["opportunity", "import-legacy-csv", str(fixture), "--dir", str(store)],
    )
    assert again.exit_code == 0
    assert "rows_skipped (duplicates): 2" in again.output


def test_import_legacy_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "opportunity",
            "import-legacy-csv",
            str(tmp_path / "missing.csv"),
            "--dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
