#!/usr/bin/env python3
"""Manual validation runner for FR-012 Submission Assistance.

Offline only — seeded Opportunity + package fixtures; no live job boards.

Examples:
  python scripts/run_fr012_submission_manual.py demo --workspace data/_fr012_m1_manual
  python scripts/run_fr012_submission_manual.py cli --workspace data/_fr012_m2_manual
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.submission import (
    FakeSubmissionAdapter,
    JsonDirectorySubmissionAttemptStore,
    ManualAssistedAdapter,
    SubmissionDuplicateError,
    SubmissionGateError,
    SubmissionOrchestrator,
)
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir

PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"
DESTINATION = "https://example.com/jobs/manual-validation"
runner = CliRunner()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FR-012 Submission Assistance manual validation"
    )
    parser.add_argument(
        "mode",
        choices=("demo", "cli"),
        nargs="?",
        default="cli",
        help="demo = library orchestrator (M1); cli = cic submission (M2)",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace for opportunities, packages, and submission attempts",
    )
    args = parser.parse_args()
    mode: str = args.mode
    default_ws = (
        _REPO_ROOT / "data" / "_fr012_m2_manual"
        if mode == "cli"
        else _REPO_ROOT / "data" / "_fr012_m1_manual"
    )
    workspace: Path = (args.workspace or default_ws).resolve()

    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    if mode == "cli":
        return _run_cli(workspace)
    return _run_demo(workspace)


def _run_demo(workspace: Path) -> int:
    print("FR-012 M1 Submission Assistance Manual Validation")
    print(f"workspace={workspace}")
    print()

    opportunities, opportunity_id, profile = seed_applied_opportunity(workspace)
    packages = package_service(workspace, opportunities, profile)
    packages.prepare(opportunity_id, **approved_gate_options())  # type: ignore[arg-type]

    attempts_root = workspace / "submission_attempts"
    store = JsonDirectorySubmissionAttemptStore(attempts_root)
    fake = FakeSubmissionAdapter()
    manual = ManualAssistedAdapter()
    orchestrator = SubmissionOrchestrator(
        opportunities,
        packages,
        store=store,
        adapters={"fake": fake, "manual_assisted": manual},
    )

    checks: list[tuple[str, bool]] = []

    try:
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=False,
            destination=DESTINATION,
        )
        checks.append(("missing approval refused", False))
    except SubmissionGateError:
        checks.append(("missing approval refused", fake.call_count == 0))

    submitted = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    checks.append(
        (
            "fake submitted with evidence",
            submitted.status == "submitted" and submitted.evidence.result_code is not None,
        )
    )

    try:
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
        checks.append(("duplicate success refused", False))
    except SubmissionDuplicateError:
        checks.append(("duplicate success refused", True))

    opportunities_b, opportunity_b, profile_b = seed_applied_opportunity(
        workspace / "opp_b"
    )
    packages_b = package_service(workspace / "pkg_b", opportunities_b, profile_b)
    packages_b.prepare(opportunity_b, **approved_gate_options())  # type: ignore[arg-type]
    fake_b = FakeSubmissionAdapter(outcome="outcome_unknown")
    store_b = JsonDirectorySubmissionAttemptStore(workspace / "attempts_b")
    orch_b = SubmissionOrchestrator(
        opportunities_b,
        packages_b,
        store=store_b,
        adapters={
            "fake": fake_b,
            "manual_assisted": ManualAssistedAdapter(),
        },
    )

    unknown = orch_b.submit(
        opportunity_b,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    checks.append(("outcome_unknown preserved", unknown.status == "outcome_unknown"))
    try:
        orch_b.submit(
            opportunity_b,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
        checks.append(("outcome_unknown not auto-retried", False))
    except SubmissionDuplicateError:
        checks.append(("outcome_unknown not auto-retried", True))

    assisted = orch_b.submit(
        opportunity_b,
        channel="manual_assisted",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    checks.append(
        (
            "manual_assisted returns manual_action_required",
            assisted.status == "manual_action_required",
        )
    )

    completed = orch_b.record_manual_completion(
        opportunity_b,
        owner_approved_submit=True,
        attestation="Owner completed application on employer site",
        destination=DESTINATION,
        confirmation_reference="MANUAL-1",
    )
    checks.append(
        (
            "manual completion recorded",
            completed.status == "manual_completed"
            and completed.attempt_id == assisted.attempt_id,
        )
    )

    reloaded = JsonDirectorySubmissionAttemptStore(workspace / "attempts_b").load(
        completed.attempt_id
    )
    checks.append(("JSON reload", reloaded.status == "manual_completed"))

    return _print_checks(checks)


def _run_cli(workspace: Path) -> int:
    print("FR-012 M2 Submission CLI Manual Validation")
    print(f"workspace={workspace}")

    _opportunities, opportunity_id, _profile = seed_applied_opportunity(
        workspace,
        source_url="https://au.seek.com/job/50101010",
        title="AI Engineer",
        company="CLI Submit Co",
        raw_text=(
            "AI Engineer. Python and LLMs. Hybrid Sydney. "
            "CLI Submit Co offline validation posting."
        ),
    )
    packages = package_service(workspace, _opportunities, _profile)
    packages.prepare(opportunity_id, **approved_gate_options())  # type: ignore[arg-type]
    print(f"opportunity_id={opportunity_id}")

    common = [
        "--dir",
        str(workspace),
        "--packages-dir",
        str(workspace / "application_packages"),
        "--attempts-dir",
        str(workspace / "submission_attempts"),
        "--cv-dir",
        str(workspace / "cv_generated"),
        "--cover-letter-dir",
        str(workspace / "cover_letter_generated"),
        "--profile",
        str(PROFILE),
    ]
    destination = ["--destination", DESTINATION]
    checks: list[tuple[str, bool]] = []

    checked = runner.invoke(app, ["submission", "check", opportunity_id, *common])
    checks.append(("submission check ready", checked.exit_code == 0 and "Submission Ready" in checked.output))

    refused = runner.invoke(
        app,
        ["submission", "run", opportunity_id, *common, "--channel", "fake", *destination],
    )
    checks.append(
        (
            "run without --approve-submit refused",
            refused.exit_code == 1 and "Owner Approval Required" in refused.output,
        )
    )

    submitted = runner.invoke(
        app,
        [
            "submission",
            "run",
            opportunity_id,
            *common,
            "--channel",
            "fake",
            "--approve-submit",
            *destination,
            "--fake-outcome",
            "submitted",
        ],
    )
    checks.append(
        (
            "fake submitted",
            submitted.exit_code == 0 and "Submission Completed" in submitted.output,
        )
    )
    attempt_id = next(
        line.split(": ", 1)[1].strip()
        for line in submitted.output.splitlines()
        if line.startswith("attempt_id:")
    )

    duplicate = runner.invoke(
        app,
        [
            "submission",
            "run",
            opportunity_id,
            *common,
            "--channel",
            "fake",
            "--approve-submit",
            *destination,
            "--fake-outcome",
            "submitted",
        ],
    )
    checks.append(
        (
            "duplicate refused",
            duplicate.exit_code == 1 and "Duplicate Submission Blocked" in duplicate.output,
        )
    )

    # Second opportunity for unknown / manual paths
    ops_b, oid_b, profile_b = seed_applied_opportunity(workspace / "opp_b")
    packages_b = package_service(workspace / "pkg_b", ops_b, profile_b)
    packages_b.prepare(oid_b, **approved_gate_options())  # type: ignore[arg-type]
    common_b = [
        "--dir",
        str(workspace / "opp_b"),
        "--packages-dir",
        str(workspace / "pkg_b" / "application_packages"),
        "--attempts-dir",
        str(workspace / "attempts_b"),
        "--cv-dir",
        str(workspace / "pkg_b" / "cv_generated"),
        "--cover-letter-dir",
        str(workspace / "pkg_b" / "cover_letter_generated"),
        "--profile",
        str(PROFILE),
    ]

    unknown = runner.invoke(
        app,
        [
            "submission",
            "run",
            oid_b,
            *common_b,
            "--channel",
            "fake",
            "--approve-submit",
            *destination,
            "--fake-outcome",
            "outcome_unknown",
        ],
    )
    checks.append(
        (
            "outcome_unknown exit non-zero",
            unknown.exit_code == 1 and "Outcome Unknown" in unknown.output,
        )
    )

    assisted = runner.invoke(
        app,
        [
            "submission",
            "run",
            oid_b,
            *common_b,
            "--channel",
            "manual_assisted",
            "--approve-submit",
            *destination,
        ],
    )
    checks.append(
        (
            "manual_assisted path",
            assisted.exit_code == 1 and "Manual Action Required" in assisted.output,
        )
    )

    completed = runner.invoke(
        app,
        [
            "submission",
            "record-manual",
            oid_b,
            *common_b,
            "--approve-submit",
            "--attestation",
            "Submitted on employer site",
            *destination,
            "--confirmation-reference",
            "CLI-1",
        ],
    )
    checks.append(
        (
            "record-manual",
            completed.exit_code == 0 and "Attempt Recorded" in completed.output,
        )
    )

    shown = runner.invoke(app, ["submission", "show", attempt_id, *common])
    checks.append(("show attempt", shown.exit_code == 0 and attempt_id in shown.output))

    listed = runner.invoke(app, ["submission", "list", *common])
    checks.append(("list attempts", listed.exit_code == 0 and attempt_id in listed.output))

    reloaded = JsonDirectorySubmissionAttemptStore(
        workspace / "submission_attempts"
    ).load(attempt_id)
    checks.append(("JSON reload after restart", reloaded.status == "submitted"))

    return _print_checks(checks)


def _print_checks(checks: list[tuple[str, bool]]) -> int:
    print("Checks:")
    all_ok = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        all_ok = all_ok and ok
    print()
    if all_ok:
        print("RESULT: PASS")
        return 0
    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
