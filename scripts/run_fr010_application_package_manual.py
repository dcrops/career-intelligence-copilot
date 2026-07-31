#!/usr/bin/env python3
"""Manual validation runner for FR-010 Application Package Preparation.

Covers M0 composition, M1 durability / regeneration, and M2 owner CLI.

Examples:
  python scripts/run_fr010_application_package_manual.py demo \\
      --workspace data/_fr010_m1_manual
  python scripts/run_fr010_application_package_manual.py cli \\
      --workspace data/_fr010_m2_manual
  python scripts/run_fr010_application_package_manual.py prepare \\
      --opportunities data/_fr010_m2_manual/opportunities \\
      --packages data/_fr010_m2_manual/application_packages \\
      --opportunity-id opp_01...
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.application_package import (
    ApplicationPackageEligibilityError,
    ApplicationPackageService,
)
from career_intelligence.application_strategy import ApplicationStrategyService
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.cli.main import app as cic_app
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanOptions,
)
from career_intelligence.cv_generation import CvGenerationOptions, TailoringOptions
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import posting_ai_engineer
from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_assessment import OpportunityAssessmentService
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.portfolio_matching import PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import (
    DeterministicMatcher,
)
from career_intelligence.profile import CareerProfile, CareerProfileService

STAMP = datetime(2026, 7, 30, 15, 0, 0, tzinfo=UTC)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PROFILE = _REPO_ROOT / "data" / "career_profile.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FR-010 Application Package Preparation manual validation (M0–M2)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser(
        "demo",
        help="Seed, prepare, reload, regenerate, prove idempotency (offline)",
    )
    demo.add_argument("--workspace", type=Path, required=True)
    demo.add_argument("--profile-path", type=Path, default=None)

    cli = sub.add_parser(
        "cli",
        help="Seed apply Opportunity and exercise cic package prepare/show/verify",
    )
    cli.add_argument("--workspace", type=Path, required=True)
    cli.add_argument("--profile-path", type=Path, default=None)

    prepare = sub.add_parser(
        "prepare",
        help="Prepare package for an existing apply Opportunity (service API)",
    )
    prepare.add_argument("--opportunities", type=Path, required=True)
    prepare.add_argument("--packages", type=Path, required=True)
    prepare.add_argument("--opportunity-id", type=str, required=True)
    prepare.add_argument("--profile-path", type=Path, default=None)
    prepare.add_argument("--cv-output-dir", type=Path, default=None)
    prepare.add_argument("--cover-letter-output-dir", type=Path, default=None)
    return parser


def _load_profile(path: Path | None) -> CareerProfile:
    if path is not None:
        return CareerProfileService.from_path(path).load()
    return CareerProfileService().load()


def _approved_options(*, override_material_benefit: bool = False) -> dict[str, object]:
    return {
        "tailoring_options": TailoringOptions(
            owner_approved_to_tailor=True,
            override_material_benefit=override_material_benefit,
        ),
        "cv_options": CvGenerationOptions(tailoring_plan_approved=True),
        "cover_letter_plan_options": CoverLetterPlanOptions(
            owner_approved_to_plan=True,
            override_material_benefit=override_material_benefit,
        ),
        "cover_letter_options": CoverLetterGenerationOptions(
            cover_letter_plan_approved=True
        ),
        "prepared_at": STAMP,
    }


def _print_manifest(manifest) -> None:
    print("-" * 72)
    print(f"Package opportunity_id={manifest.opportunity_id}")
    print(f"  prepared_at={manifest.prepared_at.isoformat()}")
    print(f"  owner_review_required={manifest.owner_review_required}")
    print("  evidence artefact paths:")
    for name, relative in sorted(manifest.evidence.artifact_paths.items()):
        print(f"    {name}: {relative}")
    acq = manifest.evidence.acquisition
    print(
        f"  acquisition: source_kind={acq.source_kind} "
        f"company={acq.company!r} title={acq.title!r}"
    )
    if acq.source_url is not None:
        print(f"  source_url={acq.source_url}")
    print("  CV drafts:")
    print(f"    markdown={manifest.cv.markdown_path}")
    print(f"    html={manifest.cv.html_path}")
    print(f"    plan={manifest.cv.plan_json_path}")
    print("  Cover letter drafts:")
    print(f"    markdown={manifest.cover_letter.markdown_path}")
    print(f"    html={manifest.cover_letter.html_path}")
    print(f"    plan={manifest.cover_letter.plan_json_path}")
    print("-" * 72)


def _seed_opportunity(
    opportunities: OpportunityService, profile: CareerProfile
) -> str:
    """Persist one offline Opportunity from fixture posting + deterministic planners."""
    posting = posting_ai_engineer()
    analysis = JobAnalysisService(FixtureExtractor()).analyse(posting)
    assessment = OpportunityAssessmentService(FixtureAssessor()).assess(
        analysis, profile
    )
    match = PortfolioMatchingService(DeterministicMatcher()).match(analysis, profile)
    strategy = ApplicationStrategyService(DeterministicStrategyPlanner()).plan(
        assessment, match, profile
    )
    opportunity = opportunities.create_from_strategy(
        posting=posting,
        job_analysis=analysis,
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    return opportunity.opportunity_id


def run_demo(args: argparse.Namespace) -> int:
    workspace = args.workspace
    opportunities_dir = workspace / "opportunities"
    packages_dir = workspace / "application_packages"
    cv_dir = workspace / "cv_generated"
    cover_dir = workspace / "cover_letter_generated"
    profile = _load_profile(args.profile_path)

    print("=" * 72)
    print("FR-010 M1 Application Package Durability Manual Validation")
    print("=" * 72)

    opportunities = OpportunityService.from_path(opportunities_dir)
    opportunity_id = _seed_opportunity(opportunities, profile)
    print(f"A. Persisted Opportunity {opportunity_id} (decision=None)")

    service = ApplicationPackageService(
        opportunities,
        profile=profile,
        packages_root=packages_dir,
        cv_output_dir=cv_dir,
        cover_letter_output_dir=cover_dir,
    )

    print("B. Non-apply must fail closed")
    try:
        service.prepare(opportunity_id, **_approved_options())
        print("  FAILED: undecided Opportunity prepared a package")
        return 1
    except ApplicationPackageEligibilityError as error:
        print(f"  refused undecided: {error}")

    opportunities.record_decision(opportunity_id, "skip")
    try:
        service.prepare(opportunity_id, **_approved_options())
        print("  FAILED: skip Opportunity prepared a package")
        return 1
    except ApplicationPackageEligibilityError as error:
        print(f"  refused skip: {error}")

    opportunities.record_decision(opportunity_id, "apply")
    print("C. Record apply and prepare package")
    strategy_summary = opportunities.get(opportunity_id).strategy_summary
    print(
        f"  strategy tier={strategy_summary.application_tier if strategy_summary else None} "
        f"(may require override_material_benefit)"
    )
    before = {
        name: (opportunities_dir / relative).read_bytes()
        for name, relative in opportunities.get(opportunity_id).artifact_paths.items()
    }
    options = _approved_options(override_material_benefit=True)
    manifest = service.prepare(opportunity_id, **options)
    _print_manifest(manifest)
    print(f"  exists={service.exists(opportunity_id)}")

    print("D. Reload + relative persistence")
    reloaded = service.get(opportunity_id)
    assert reloaded.model_dump() == manifest.model_dump()
    raw = json.loads(
        (packages_dir / opportunity_id / "manifest.json").read_text(encoding="utf-8")
    )
    print("  reload equal: True")
    print(f"  persisted relative CV path: {raw['cv']['markdown_path']}")
    print(
        "  resolved absolute CV path ends with stem: "
        f"{Path(reloaded.cv.markdown_path).name == f'{opportunity_id}.md'}"
    )

    print("E. Idempotent prepare (same prepared_at)")
    again = service.prepare(opportunity_id, **options)
    cv_bytes = Path(manifest.cv.markdown_path).read_bytes()
    print(f"  manifest equal: {again == manifest}")
    print(
        f"  CV bytes unchanged: "
        f"{Path(again.cv.markdown_path).read_bytes() == cv_bytes}"
    )

    print("F. Repeated regeneration (replace semantics)")
    previous = again
    for hour in (16, 17, 18):
        regen_options = {**options, "prepared_at": STAMP.replace(hour=hour)}
        current = service.prepare(opportunity_id, **regen_options)
        print(
            f"  hour={hour} prepared_at={current.prepared_at.isoformat()} "
            f"same_paths={current.cv.markdown_path == previous.cv.markdown_path}"
        )
        previous = current

    print("G. Immutable upstream artefacts")
    after = opportunities.get(opportunity_id)
    unchanged = all(
        (opportunities_dir / relative).read_bytes() == before[name]
        for name, relative in after.artifact_paths.items()
    )
    print(f"  FR-002–FR-005 bytes unchanged: {unchanged}")
    print(
        "  decision still apply: "
        f"{after.decision is not None and after.decision.decision == 'apply'}"
    )
    print(f"  status unchanged (still assessed): {after.status == 'assessed'}")
    print(f"  final prepared_at: {service.get(opportunity_id).prepared_at.isoformat()}")
    return 0 if unchanged and again == manifest else 1


def run_cli(args: argparse.Namespace) -> int:
    workspace = args.workspace
    opportunities_dir = workspace / "opportunities"
    packages_dir = workspace / "application_packages"
    cv_dir = workspace / "cv_generated"
    cover_dir = workspace / "cover_letter_generated"
    profile_path = args.profile_path or _DEFAULT_PROFILE
    profile = _load_profile(profile_path)

    print("=" * 72)
    print("FR-010 M2 Application Package CLI Manual Validation")
    print("=" * 72)

    opportunities = OpportunityService.from_path(opportunities_dir)
    opportunity_id = _seed_opportunity(opportunities, profile)
    opportunities.record_decision(opportunity_id, "apply")
    print(f"A. Seeded apply Opportunity {opportunity_id}")

    runner = CliRunner()
    common = [
        "--dir",
        str(opportunities_dir),
        "--packages-dir",
        str(packages_dir),
        "--cv-dir",
        str(cv_dir),
        "--cover-letter-dir",
        str(cover_dir),
        "--profile",
        str(profile_path),
    ]

    print("B. CLI prepare without --approve must fail closed")
    refused = runner.invoke(cic_app, ["package", "prepare", opportunity_id, *common])
    print(f"  exit={refused.exit_code}")
    last = refused.output.strip().splitlines()[-1] if refused.output.strip() else ""
    print(f"  message={last}")
    if refused.exit_code == 0:
        print("  FAILED: prepare succeeded without --approve")
        return 1

    print("C. CLI prepare --approve --override-material-benefit")
    prepared = runner.invoke(
        cic_app,
        [
            "package",
            "prepare",
            opportunity_id,
            *common,
            "--approve",
            "--override-material-benefit",
        ],
    )
    print(prepared.output.rstrip())
    if prepared.exit_code != 0:
        print("  FAILED: prepare")
        return 1

    print("D. CLI show")
    shown = runner.invoke(cic_app, ["package", "show", opportunity_id, *common])
    print(shown.output.rstrip())
    if shown.exit_code != 0:
        print("  FAILED: show")
        return 1

    print("E. CLI verify")
    verified = runner.invoke(cic_app, ["package", "verify", opportunity_id, *common])
    print(verified.output.rstrip())
    if verified.exit_code != 0:
        print("  FAILED: verify")
        return 1

    print("F. CLI show --yaml includes evidence")
    yaml_shown = runner.invoke(
        cic_app, ["package", "show", opportunity_id, *common, "--yaml"]
    )
    ok = (
        yaml_shown.exit_code == 0
        and "artifact_paths:" in yaml_shown.output
        and opportunity_id in yaml_shown.output
    )
    print(f"  yaml ok: {ok}")
    return 0 if ok else 1


def run_prepare(args: argparse.Namespace) -> int:
    opportunities = OpportunityService.from_path(args.opportunities)
    opportunity = opportunities.get(args.opportunity_id)
    if opportunity.decision is None or opportunity.decision.decision != "apply":
        kind = (
            opportunity.decision.decision
            if opportunity.decision is not None
            else "none"
        )
        print(
            f"Refusing prepare: decision must be apply (got {kind}) "
            f"for {args.opportunity_id}"
        )
        return 1

    profile = _load_profile(args.profile_path)
    service = ApplicationPackageService(
        opportunities,
        profile=profile,
        packages_root=args.packages,
        cv_output_dir=args.cv_output_dir
        or (_REPO_ROOT / "career-documents" / "cv" / "generated"),
        cover_letter_output_dir=args.cover_letter_output_dir
        or (_REPO_ROOT / "career-documents" / "cover-letters" / "generated"),
    )
    manifest = service.prepare(
        args.opportunity_id, **_approved_options(override_material_benefit=True)
    )
    _print_manifest(manifest)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        return run_prepare(args)
    if args.command == "cli":
        return run_cli(args)
    return run_demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
