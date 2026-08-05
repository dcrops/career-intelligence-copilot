"""CLI tests for FR-010 M2 application package owner operations."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from tests.unit.application_package.helpers import seed_applied_opportunity
from tests.unit.application_strategy.helpers import fixtures_dir

runner = CliRunner()
PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"


def _paths(tmp_path: Path) -> dict[str, str]:
    return {
        "dir": str(tmp_path),
        "packages": str(tmp_path / "application_packages"),
        "cv": str(tmp_path / "cv_generated"),
        "cover": str(tmp_path / "cover_letter_generated"),
        "profile": str(PROFILE),
        "truth": str(tmp_path / "truth_reports"),
    }


def _prepare_args(oid: str, paths: dict[str, str], *extra: str) -> list[str]:
    return [
        "package",
        "prepare",
        oid,
        "--dir",
        paths["dir"],
        "--packages-dir",
        paths["packages"],
        "--cv-dir",
        paths["cv"],
        "--cover-letter-dir",
        paths["cover"],
        "--profile",
        paths["profile"],
        *extra,
    ]


def test_prepare_requires_explicit_approve(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)
    result = runner.invoke(app, _prepare_args(oid, paths))
    assert result.exit_code == 1
    assert "--approve" in result.output
    assert "Refusing prepare" in result.output


def test_prepare_show_and_verify_happy_path(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)

    prepared = runner.invoke(app, _prepare_args(oid, paths, "--approve"))
    assert prepared.exit_code == 0, prepared.output
    assert oid in prepared.output
    assert "owner_review_required" in prepared.output
    assert "Prepared application package" in prepared.output

    shown = runner.invoke(
        app,
        [
            "package",
            "show",
            oid,
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--cv-dir",
            paths["cv"],
            "--cover-letter-dir",
            paths["cover"],
            "--profile",
            paths["profile"],
        ],
    )
    assert shown.exit_code == 0, shown.output
    assert oid in shown.output
    assert "cv:" in shown.output
    assert "cover_letter:" in shown.output

    validated = runner.invoke(
        app,
        [
            "truth",
            "validate-package",
            oid,
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--cv-dir",
            paths["cv"],
            "--cover-letter-dir",
            paths["cover"],
            "--profile",
            paths["profile"],
            "--truth-reports-dir",
            paths["truth"],
        ],
    )
    assert validated.exit_code == 0, validated.output

    verified = runner.invoke(
        app,
        [
            "package",
            "verify",
            oid,
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--cv-dir",
            paths["cv"],
            "--cover-letter-dir",
            paths["cover"],
            "--profile",
            paths["profile"],
            "--truth-reports-dir",
            paths["truth"],
        ],
    )
    assert verified.exit_code == 0, verified.output
    assert "is intact" in verified.output
    assert "ALLOWED" in verified.output


def test_prepare_yaml_and_show_yaml(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)

    prepared = runner.invoke(app, _prepare_args(oid, paths, "--approve", "--yaml"))
    assert prepared.exit_code == 0, prepared.output
    assert "opportunity_id:" in prepared.output
    assert "artifact_paths:" in prepared.output

    shown = runner.invoke(
        app,
        [
            "package",
            "show",
            oid,
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--cv-dir",
            paths["cv"],
            "--cover-letter-dir",
            paths["cover"],
            "--profile",
            paths["profile"],
            "--yaml",
        ],
    )
    assert shown.exit_code == 0
    assert "owner_review_required: true" in shown.output


def test_prepare_rejects_non_apply(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path, decision="skip")
    paths = _paths(tmp_path)
    result = runner.invoke(app, _prepare_args(oid, paths, "--approve"))
    assert result.exit_code == 1
    assert "apply" in result.output.lower()


def test_show_missing_package(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)
    result = runner.invoke(
        app,
        [
            "package",
            "show",
            oid,
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--cv-dir",
            paths["cv"],
            "--cover-letter-dir",
            paths["cover"],
            "--profile",
            paths["profile"],
        ],
    )
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_verify_detects_missing_draft(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)
    prepared = runner.invoke(app, _prepare_args(oid, paths, "--approve"))
    assert prepared.exit_code == 0, prepared.output

    draft = tmp_path / "cv_generated" / f"{oid}.md"
    assert draft.is_file()
    draft.unlink()

    verified = runner.invoke(
        app,
        [
            "package",
            "verify",
            oid,
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--cv-dir",
            paths["cv"],
            "--cover-letter-dir",
            paths["cover"],
            "--profile",
            paths["profile"],
        ],
    )
    assert verified.exit_code == 1
    assert "missing draft" in verified.output.lower()


def test_show_no_verify_loads_when_draft_missing(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)
    prepared = runner.invoke(app, _prepare_args(oid, paths, "--approve"))
    assert prepared.exit_code == 0, prepared.output
    (tmp_path / "cv_generated" / f"{oid}.md").unlink()

    shown = runner.invoke(
        app,
        [
            "package",
            "show",
            oid,
            "--dir",
            paths["dir"],
            "--packages-dir",
            paths["packages"],
            "--cv-dir",
            paths["cv"],
            "--cover-letter-dir",
            paths["cover"],
            "--profile",
            paths["profile"],
            "--no-verify",
        ],
    )
    assert shown.exit_code == 0, shown.output
    assert oid in shown.output
