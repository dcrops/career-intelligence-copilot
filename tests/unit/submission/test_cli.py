"""CLI tests for FR-012 M2 owner-operable submission workflow."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.submission import JsonDirectorySubmissionAttemptStore
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir

runner = CliRunner()
PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"
DESTINATION = "https://example.com/jobs/cli"


def _paths(tmp_path: Path) -> dict[str, str]:
    return {
        "dir": str(tmp_path),
        "packages": str(tmp_path / "application_packages"),
        "attempts": str(tmp_path / "submission_attempts"),
        "cv": str(tmp_path / "cv_generated"),
        "cover": str(tmp_path / "cover_letter_generated"),
        "profile": str(PROFILE),
        "truth": str(tmp_path / "truth_reports"),
    }


def _common(paths: dict[str, str]) -> list[str]:
    return [
        "--dir",
        paths["dir"],
        "--packages-dir",
        paths["packages"],
        "--attempts-dir",
        paths["attempts"],
        "--cv-dir",
        paths["cv"],
        "--cover-letter-dir",
        paths["cover"],
        "--profile",
        paths["profile"],
        "--truth-reports-dir",
        paths["truth"],
    ]


def _prepare(tmp_path: Path) -> tuple[str, dict[str, str]]:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    paths = _paths(tmp_path)
    from career_intelligence.truth_validation import (
        JsonDirectoryTruthReportStore,
        evaluate_package_truth,
    )

    evaluate_package_truth(
        manifest=packages.get(oid, verify=True),
        profile=profile,
        store=JsonDirectoryTruthReportStore(Path(paths["truth"])),
        revalidate=True,
    )
    return oid, paths


def _attempt_id(output: str) -> str:
    return next(
        line.split(": ", 1)[1].strip()
        for line in output.splitlines()
        if line.startswith("attempt_id:")
    )


def test_submission_check_ready(tmp_path: Path) -> None:
    oid, paths = _prepare(tmp_path)
    result = runner.invoke(app, ["submission", "check", oid, *_common(paths)])
    assert result.exit_code == 0, result.output
    assert "Submission Ready" in result.output
    assert "fake" in result.output
    assert "manual_assisted" in result.output
    store = JsonDirectorySubmissionAttemptStore(Path(paths["attempts"]))
    assert store.list() == []


def test_submission_check_not_ready_without_package(tmp_path: Path) -> None:
    _opportunities, oid, _profile = seed_applied_opportunity(tmp_path)
    paths = _paths(tmp_path)
    result = runner.invoke(app, ["submission", "check", oid, *_common(paths)])
    assert result.exit_code == 1
    assert "Submission Not Ready" in result.output


def test_submission_run_requires_approve(tmp_path: Path) -> None:
    oid, paths = _prepare(tmp_path)
    result = runner.invoke(
        app,
        [
            "submission",
            "run",
            oid,
            *_common(paths),
            "--channel",
            "fake",
            "--destination",
            DESTINATION,
        ],
    )
    assert result.exit_code == 1
    assert "Owner Approval Required" in result.output
    assert JsonDirectorySubmissionAttemptStore(Path(paths["attempts"])).list() == []


def test_submission_run_fake_success(tmp_path: Path) -> None:
    oid, paths = _prepare(tmp_path)
    result = runner.invoke(
        app,
        [
            "submission",
            "run",
            oid,
            *_common(paths),
            "--channel",
            "fake",
            "--approve-submit",
            "--destination",
            DESTINATION,
            "--fake-outcome",
            "submitted",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Submission Completed" in result.output
    assert "status: submitted" in result.output
    attempt_id = _attempt_id(result.output)

    shown = runner.invoke(
        app, ["submission", "show", attempt_id, *_common(paths)]
    )
    assert shown.exit_code == 0, shown.output
    assert attempt_id in shown.output
    assert "status: submitted" in shown.output

    listed = runner.invoke(app, ["submission", "list", *_common(paths)])
    assert listed.exit_code == 0
    assert attempt_id in listed.output


def test_submission_run_duplicate_blocked(tmp_path: Path) -> None:
    oid, paths = _prepare(tmp_path)
    args = [
        "submission",
        "run",
        oid,
        *_common(paths),
        "--channel",
        "fake",
        "--approve-submit",
        "--destination",
        DESTINATION,
        "--fake-outcome",
        "submitted",
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, args)
    assert second.exit_code == 1
    assert "Duplicate Submission Blocked" in second.output


def test_submission_run_manual_assisted(tmp_path: Path) -> None:
    oid, paths = _prepare(tmp_path)
    result = runner.invoke(
        app,
        [
            "submission",
            "run",
            oid,
            *_common(paths),
            "--channel",
            "manual_assisted",
            "--approve-submit",
            "--destination",
            DESTINATION,
        ],
    )
    assert result.exit_code == 1
    assert "Manual Action Required" in result.output
    assert "status: manual_action_required" in result.output


def test_submission_run_outcome_unknown(tmp_path: Path) -> None:
    oid, paths = _prepare(tmp_path)
    result = runner.invoke(
        app,
        [
            "submission",
            "run",
            oid,
            *_common(paths),
            "--channel",
            "fake",
            "--approve-submit",
            "--destination",
            DESTINATION,
            "--fake-outcome",
            "outcome_unknown",
        ],
    )
    assert result.exit_code == 1
    assert "Outcome Unknown" in result.output
    assert "status: outcome_unknown" in result.output


def test_submission_record_manual(tmp_path: Path) -> None:
    oid, paths = _prepare(tmp_path)
    result = runner.invoke(
        app,
        [
            "submission",
            "record-manual",
            oid,
            *_common(paths),
            "--approve-submit",
            "--attestation",
            "Submitted on employer portal",
            "--destination",
            DESTINATION,
            "--confirmation-reference",
            "CONF-1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Attempt Recorded" in result.output
    assert "status: manual_completed" in result.output
    assert "manual_owner_completed" in result.output


def test_submission_show_missing(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    result = runner.invoke(
        app,
        [
            "submission",
            "show",
            "sub_01K00000000000000000000000",
            *_common(paths),
        ],
    )
    assert result.exit_code == 1
    assert "not found" in result.output.lower()
