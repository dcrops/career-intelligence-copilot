"""CLI tests for FR-011 M1 preparation orchestration owner operations."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from tests.unit.application_package.helpers import (
    package_service,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir

runner = CliRunner()
PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"


def _paths(tmp_path: Path) -> dict[str, str]:
    return {
        "dir": str(tmp_path),
        "packages": str(tmp_path / "application_packages"),
        "runs": str(tmp_path / "preparation_runs"),
        "cv": str(tmp_path / "cv_generated"),
        "cover": str(tmp_path / "cover_letter_generated"),
        "profile": str(PROFILE),
    }


def _run_args(oid: str, paths: dict[str, str], *extra: str) -> list[str]:
    return [
        "preparation",
        "run",
        oid,
        "--dir",
        paths["dir"],
        "--packages-dir",
        paths["packages"],
        "--runs-dir",
        paths["runs"],
        "--cv-dir",
        paths["cv"],
        "--cover-letter-dir",
        paths["cover"],
        "--profile",
        paths["profile"],
        *extra,
    ]


def test_preparation_run_requires_explicit_approve(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)
    result = runner.invoke(app, _run_args(oid, paths))
    assert result.exit_code == 1
    assert "--approve" in result.output
    assert "Refusing preparation run" in result.output


def test_preparation_run_and_show_happy_path(tmp_path: Path) -> None:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)

    prepared = runner.invoke(app, _run_args(oid, paths, "--approve"))
    assert prepared.exit_code == 0, prepared.output
    assert "Preparation orchestration completed" in prepared.output
    assert "status: completed" in prepared.output
    assert oid in prepared.output
    assert "run_id: apr_" in prepared.output

    run_id = next(
        line.split(": ", 1)[1].strip()
        for line in prepared.output.splitlines()
        if line.startswith("run_id:")
    )

    shown = runner.invoke(
        app,
        [
            "preparation",
            "show",
            run_id,
            "--runs-dir",
            paths["runs"],
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--profile",
            paths["profile"],
        ],
    )
    assert shown.exit_code == 0, shown.output
    assert run_id in shown.output
    assert "status: completed" in shown.output

    packages = package_service(tmp_path, opportunities, profile)
    manifest = packages.get(oid, verify=True)
    assert manifest.opportunity_id == oid


def test_preparation_non_apply_fails_deterministically(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path, decision="skip")
    paths = _paths(tmp_path)
    result = runner.invoke(app, _run_args(oid, paths, "--approve"))
    assert result.exit_code == 1
    assert "status: failed" in result.output
    assert "validate_preconditions" in result.output


def test_preparation_show_missing_run(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    result = runner.invoke(
        app,
        [
            "preparation",
            "show",
            "apr_01K00000000000000000000000",
            "--runs-dir",
            paths["runs"],
        ],
    )
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_preparation_yaml_run(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)
    result = runner.invoke(app, _run_args(oid, paths, "--approve", "--yaml"))
    assert result.exit_code == 0, result.output
    assert "status: completed" in result.output or "status: completed" in result.stdout
    # YAML dump uses the field value
    assert "completed" in result.output
    assert "apr_" in result.output
