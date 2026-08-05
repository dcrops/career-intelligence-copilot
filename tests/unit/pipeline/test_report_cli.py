"""CLI tests for FR-013 M4 report / due / export."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from tests.unit.opportunities.helpers import create_opportunity

runner = CliRunner()


def _seed(tmp_path: Path) -> tuple[str, list[str]]:
    _, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    common = [
        "--dir",
        str(tmp_path / "opportunities"),
        "--events-dir",
        str(tmp_path / "pipeline_events"),
    ]
    oid = opportunity.opportunity_id
    assert runner.invoke(app, ["pipeline", "submit", oid, *common]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["pipeline", "follow-up", oid, *common, "--date", "2026-01-01"],
        ).exit_code
        == 0
    )
    return oid, common


def test_pipeline_report_due_export(tmp_path: Path) -> None:
    oid, common = _seed(tmp_path)
    report = runner.invoke(app, ["pipeline", "report", *common])
    assert report.exit_code == 0, report.output
    assert "Pipeline Report" in report.output
    assert "submitted_cohort:" in report.output

    due = runner.invoke(app, ["pipeline", "due", *common, "--on", "2026-08-05"])
    assert due.exit_code == 0, due.output
    assert oid in due.output
    assert "overdue" in due.output

    out = tmp_path / "out.csv"
    exported = runner.invoke(
        app,
        ["pipeline", "export", *common, "--output", str(out)],
    )
    assert exported.exit_code == 0, exported.output
    assert out.is_file()
    assert oid in out.read_text(encoding="utf-8-sig")
