"""Manual validation runner for FR-011 Application Preparation Orchestration.

Offline only — uses seeded Opportunity fixtures; no live acquisition.

Examples:
  python scripts/run_fr011_preparation_manual.py demo \\
      --workspace data/_fr011_m0_manual
  python scripts/run_fr011_preparation_manual.py cli \\
      --workspace data/_fr011_m1_manual
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

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.application_preparation import (
    ApplicationPreparationOrchestrator,
)
from career_intelligence.cli.main import app
from tests.unit.application_package.helpers import (
    approved_gate_options,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir

PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"
runner = CliRunner()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FR-011 Application Preparation Orchestration manual validation"
    )
    parser.add_argument(
        "mode",
        choices=("demo", "cli"),
        nargs="?",
        default="demo",
        help="demo = library orchestrator (M0); cli = cic preparation (M1)",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace directory for opportunities, packages, and preparation runs",
    )
    args = parser.parse_args()
    mode: str = args.mode
    default_ws = (
        _REPO_ROOT / "data" / "_fr011_m1_manual"
        if mode == "cli"
        else _REPO_ROOT / "data" / "_fr011_m0_manual"
    )
    workspace: Path = (args.workspace or default_ws).resolve()

    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    if mode == "cli":
        return _run_cli(workspace)
    return _run_demo(workspace)


def _run_demo(workspace: Path) -> int:
    print("FR-011 M0 Application Preparation Manual Validation")
    print(f"workspace={workspace}")

    opportunities, opportunity_id, profile = seed_applied_opportunity(
        workspace,
        source_url="https://au.seek.com/job/30101010",
        title="AI Engineer",
        company="Manual Prep Co",
        raw_text=(
            "AI Engineer. Python and LLMs. Hybrid Sydney. "
            "Manual Prep Co offline validation posting."
        ),
    )
    print(f"opportunity_id={opportunity_id}")

    packages = ApplicationPackageService(
        opportunities,
        profile=profile,
        packages_root=workspace / "application_packages",
        cv_output_dir=workspace / "cv_generated",
        cover_letter_output_dir=workspace / "cover_letter_generated",
    )
    orchestrator = ApplicationPreparationOrchestrator(
        opportunities,
        packages,
        runs_root=workspace / "preparation_runs",
    )

    skip_ops, skip_id, skip_profile = seed_applied_opportunity(
        workspace / "skip_workspace",
        decision="skip",
        source_url="https://au.seek.com/job/30101011",
        title="Other Role",
        company="Skip Co",
        raw_text="Other Role. SQL only. Skip Co body for manual check.",
    )
    skip_packages = ApplicationPackageService(
        skip_ops,
        profile=skip_profile,
        packages_root=workspace / "skip_workspace" / "application_packages",
        cv_output_dir=workspace / "skip_workspace" / "cv_generated",
        cover_letter_output_dir=workspace / "skip_workspace" / "cover_letter_generated",
    )
    skip_orch = ApplicationPreparationOrchestrator(
        skip_ops,
        skip_packages,
        runs_root=workspace / "skip_workspace" / "preparation_runs",
    )
    skipped = skip_orch.run(skip_id, **approved_gate_options())
    assert skipped.status == "failed"
    assert skipped.error is not None
    assert skipped.error.step_id == "validate_preconditions"
    print("PASS: non-apply fails at validate_preconditions")

    state = orchestrator.run(opportunity_id, **approved_gate_options())
    assert state.status == "completed", state.error
    assert state.package is not None
    print(f"PASS: run completed run_id={state.run_id}")

    reloaded = orchestrator.get(state.run_id)
    assert reloaded.status == "completed"
    print("PASS: run reload")

    manifest = packages.get(opportunity_id, verify=True)
    assert Path(manifest.cv.markdown_path).is_file()
    assert Path(manifest.cover_letter.markdown_path).is_file()
    print("PASS: package verify")

    print("RESULT: PASS")
    return 0


def _run_cli(workspace: Path) -> int:
    print("FR-011 M1 Application Preparation CLI Manual Validation")
    print(f"workspace={workspace}")

    _opportunities, opportunity_id, _profile = seed_applied_opportunity(
        workspace,
        source_url="https://au.seek.com/job/40101010",
        title="AI Engineer",
        company="CLI Prep Co",
        raw_text=(
            "AI Engineer. Python and LLMs. Hybrid Sydney. "
            "CLI Prep Co offline validation posting."
        ),
    )
    print(f"opportunity_id={opportunity_id}")

    common = [
        "--dir",
        str(workspace),
        "--packages-dir",
        str(workspace / "application_packages"),
        "--runs-dir",
        str(workspace / "preparation_runs"),
        "--cv-dir",
        str(workspace / "cv_generated"),
        "--cover-letter-dir",
        str(workspace / "cover_letter_generated"),
        "--profile",
        str(PROFILE),
    ]

    refused = runner.invoke(
        app, ["preparation", "run", opportunity_id, *common]
    )
    assert refused.exit_code == 1
    assert "--approve" in refused.output
    print("PASS: prepare without --approve refused")

    prepared = runner.invoke(
        app, ["preparation", "run", opportunity_id, *common, "--approve"]
    )
    assert prepared.exit_code == 0, prepared.output
    assert "status: completed" in prepared.output
    print("PASS: preparation run with --approve")

    run_id = next(
        line.split(": ", 1)[1].strip()
        for line in prepared.output.splitlines()
        if line.startswith("run_id:")
    )
    shown = runner.invoke(app, ["preparation", "show", run_id, *common])
    assert shown.exit_code == 0, shown.output
    assert run_id in shown.output
    print("PASS: preparation show")

    package_common = [
        "--dir",
        str(workspace),
        "--packages-dir",
        str(workspace / "application_packages"),
        "--cv-dir",
        str(workspace / "cv_generated"),
        "--cover-letter-dir",
        str(workspace / "cover_letter_generated"),
        "--profile",
        str(PROFILE),
    ]

    verified = runner.invoke(
        app, ["package", "verify", opportunity_id, *package_common]
    )
    assert verified.exit_code == 0, verified.output
    print("PASS: package verify after orchestration")

    yaml_out = runner.invoke(
        app, ["preparation", "show", run_id, *common, "--yaml"]
    )
    assert yaml_out.exit_code == 0
    assert "opportunity_id" in yaml_out.output
    print("PASS: show --yaml")

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
