"""CLI tests for FR-014 M3 cic truth commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir

runner = CliRunner()
PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"
REDWOLF = (
    "Roles centred on Python, TypeScript, and Vue are where I do my best "
    "engineering work."
)


def test_truth_validate_redwolf_and_show(tmp_path: Path) -> None:
    md = tmp_path / "redwolf.md"
    md.write_text(REDWOLF, encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "truth",
            "validate",
            str(md),
            "--profile",
            str(PROFILE),
            "--kind",
            "cover_letter_markdown",
            "--no-persist",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "outcome: fail" in result.output
    assert "typescript" in result.output.casefold()
    assert "vue" in result.output.casefold()


def test_truth_validate_package_and_stale_check(tmp_path: Path) -> None:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    truth = str(tmp_path / "truth")
    common = [
        "--dir",
        str(tmp_path),
        "--packages-dir",
        str(tmp_path / "application_packages"),
        "--cv-dir",
        str(tmp_path / "cv_generated"),
        "--cover-letter-dir",
        str(tmp_path / "cover_letter_generated"),
        "--profile",
        str(PROFILE),
        "--truth-reports-dir",
        truth,
    ]
    ok = runner.invoke(app, ["truth", "validate-package", oid, *common])
    assert ok.exit_code == 0, ok.output
    assert "ALLOWED" in ok.output

    manifest = packages.get(oid, verify=True)
    Path(manifest.cover_letter.markdown_path).write_text(
        Path(manifest.cover_letter.markdown_path).read_text(encoding="utf-8")
        + "\nchange\n",
        encoding="utf-8",
    )
    stale = runner.invoke(
        app, ["truth", "validate-package", oid, *common, "--check-only"]
    )
    assert stale.exit_code == 1, stale.output
    assert "BLOCKED" in stale.output
