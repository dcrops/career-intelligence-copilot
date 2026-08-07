"""FR-017 M3 — read-only metrics CLI and presentation tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.multi_agent import (
    JsonDirectoryOrchestrationStore,
    format_fixture_observability,
    format_observability_report,
    format_store_observability,
    get_demo_fixture,
    list_demo_fixture_ids,
)
from career_intelligence.multi_agent.observability_presentation import (
    evaluate_run_observability,
    format_corpus_cli,
)

runner = CliRunner()


def test_list_demo_fixtures() -> None:
    ids = list_demo_fixture_ids()
    assert "C01_complete_successful" in ids
    assert "C08_orphaned_child_ref" in ids
    assert "C14_malformed_contradictory" in ids


def test_presentation_complete_run_shows_required_fields() -> None:
    text = format_fixture_observability(get_demo_fixture("C01_complete_successful"))
    assert "Owner goal:" in text
    assert "Observed state" in text
    assert "selected=" in text
    assert "delegation=" in text
    assert "lifecycle=" in text
    assert "child_brief=" in text
    assert "Stop reason:" in text
    assert "Owner next action:" in text
    assert "Steps / visits:" in text
    assert "idempotency_key=" in text
    assert "R1-R12 reconstructability" in text
    assert "R1 PASS" in text
    assert "read-only" in text.lower()


def test_presentation_missing_versus_zero() -> None:
    missing = format_fixture_observability(
        get_demo_fixture("C06_missing_optional_metadata")
    )
    zero = format_fixture_observability(get_demo_fixture("C07_measured_zero"))
    assert "input_tokens=missing" in missing
    assert "estimated_cost_usd=missing" in missing
    assert "input_tokens=0" in zero
    assert "measured zero" in zero.lower()


def test_presentation_orphan_and_contradictory() -> None:
    orphan = format_fixture_observability(get_demo_fixture("C08_orphaned_child_ref"))
    bad = format_fixture_observability(get_demo_fixture("C14_malformed_contradictory"))
    assert "ORPHAN" in orphan
    assert "R11 FAIL" in orphan
    assert "correlation_complete=False" in orphan
    assert "R11 FAIL" in bad
    assert "ORPHAN" in bad


def test_presentation_delegation_blocked() -> None:
    text = format_fixture_observability(get_demo_fixture("C02_delegation_blocked"))
    assert "delegation=deny" in text
    assert "delegation_blocked" in text


def test_presentation_prepare_then_brief() -> None:
    text = format_fixture_observability(get_demo_fixture("C05_prepare_then_brief"))
    assert "prepare_then_brief" in text
    assert "bopa" in text
    assert "obs" in text
    assert "child_agent_run=" in text
    assert "child_brief=" in text


def test_cli_metrics_fixture() -> None:
    result = runner.invoke(
        app,
        ["agent", "orchestrate", "metrics", "--fixture", "C01_complete_successful"],
    )
    assert result.exit_code == 0, result.output
    assert "FR-017 orchestration metrics" in result.output
    assert "R1 PASS" in result.output


def test_cli_metrics_list_fixtures() -> None:
    result = runner.invoke(app, ["agent", "orchestrate", "metrics", "--list-fixtures"])
    assert result.exit_code == 0
    assert "C01_complete_successful" in result.output


def test_cli_metrics_corpus() -> None:
    result = runner.invoke(app, ["agent", "orchestrate", "metrics-corpus"])
    assert result.exit_code == 0, result.output
    assert "go_no_go=GO" in result.output
    assert "C15_mixed_corpus_aggregation" in result.output
    assert "Aggregate metrics" in result.output


def test_cli_metrics_missing_args() -> None:
    result = runner.invoke(app, ["agent", "orchestrate", "metrics"])
    assert result.exit_code == 1


def test_cli_metrics_from_store_read_only(tmp_path: Path) -> None:
    fx = get_demo_fixture("C02_delegation_blocked")
    disk = JsonDirectoryOrchestrationStore(tmp_path)
    disk.save(fx.run)
    for h in fx.handoffs:
        disk.save_handoff(h)

    run_path = tmp_path / f"{fx.run.orchestration_run_id}.json"
    before = run_path.read_text(encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "metrics",
            fx.run.orchestration_run_id,
            "--orchestration-runs-dir",
            str(tmp_path),
            "--agent-runs-dir",
            str(tmp_path / "agent_runs_empty"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "delegation=deny" in result.output
    after = run_path.read_text(encoding="utf-8")
    assert before == after  # no writes


def test_store_observability_loads_handoffs(tmp_path: Path) -> None:
    fx = get_demo_fixture("C01_complete_successful")
    disk = JsonDirectoryOrchestrationStore(tmp_path)
    disk.save(fx.run)
    for h in fx.handoffs:
        disk.save_handoff(h)
    text = format_store_observability(disk.load(fx.run.orchestration_run_id), disk)
    assert "R1 PASS" in text
    assert "child_brief=" in text


def test_evaluate_run_observability_pure() -> None:
    fx = get_demo_fixture("C07_measured_zero")
    metrics, report = evaluate_run_observability(
        fx.run, fx.handoffs, child_metrics=fx.child_metrics
    )
    assert metrics.input_tokens == 0
    assert report.all_satisfied
    text = format_observability_report(metrics, report)
    assert "input_tokens=0" in text


def test_format_corpus_cli_go() -> None:
    text = format_corpus_cli()
    assert "go_no_go=GO" in text
    assert "passed=15/15" in text
