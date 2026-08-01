#!/usr/bin/env python3
"""Manual validation runner for FR-007 Cover Letter Generation.

Upstream resolution mirrors FR-006:

1. ``--strategy-json PATH`` — reuse a saved FR-005 pipeline JSON
2. Auto-reuse — ``manual_validation/outputs/{job-file stem}.json``
3. Otherwise exit with guidance (live upstream not required for FR-007 smoke)

Examples:
  python scripts/run_cover_letter_manual.py \\
    --job-file manual_validation/jobs/002_bluefin_ai_systems_developer.txt

  python scripts/run_cover_letter_manual.py \\
    --strategy-json manual_validation/outputs/009_forever_new_senior_ai_automation_engineer_digital.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from career_intelligence.application_strategy import ApplicationStrategy
from career_intelligence.cover_letter import (
    ContactDetails,
    CoverLetter,
    CoverLetterGenerationOptions,
    CoverLetterGenerationService,
    CoverLetterPlan,
    CoverLetterPlanGateError,
    CoverLetterPlanOptions,
    CoverLetterPlanService,
    DeterministicCoverLetterPlanner,
    default_generated_dir,
    write_cover_letter_drafts,
)
from career_intelligence.profile import CareerProfile, CareerProfileService

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MANUAL_OUTPUTS = _REPO_ROOT / "manual_validation" / "outputs"

# Matches FR-006 CV manual runner — same professional suite contact block.
_DEFAULT_CONTACT = ContactDetails(
    email="djcropster@gmail.com",
    phone="0400 811 545",
    location="Melbourne, VIC",
    linkedin_url="https://www.linkedin.com/in/david-cropper/",
    portfolio_url="https://journey.chaseriskandcompliance.com.au/",
    github_url="https://github.com/dcrops",
)


@dataclass(frozen=True)
class RunResult:
    strategy: ApplicationStrategy
    plan: CoverLetterPlan | None
    letter: CoverLetter | None
    gate_message: str | None
    override_material_benefit: bool
    output_dir: Path | None
    stem: str | None
    markdown_path: Path | None
    html_path: Path | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FR-007 Cover Letter manual validation")
    parser.add_argument("--job-file", type=Path, default=None)
    parser.add_argument("--strategy-json", type=Path, default=None)
    parser.add_argument("--profile-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--not-owner-approved-to-plan",
        action="store_true",
        help="Refuse planning (default is approved for manual validation).",
    )
    parser.add_argument(
        "--not-cover-letter-plan-approved",
        action="store_true",
        help="Stop after plan (default generates letter for review).",
    )
    parser.add_argument(
        "--override-material-benefit",
        action="store_true",
        help="Override platinum/gold / consider_cover_letter material-benefit gate.",
    )
    parser.add_argument("--plan-only", action="store_true")
    return parser


def material_benefit_allows(strategy: ApplicationStrategy) -> bool:
    if strategy.application_tier in {"platinum", "gold"}:
        return True
    return any(action.kind == "consider_cover_letter" for action in strategy.next_actions)


def load_strategy_from_pipeline_json(path: Path) -> ApplicationStrategy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "application_strategy" not in payload:
        raise SystemExit(f"Pipeline JSON missing 'application_strategy': {path}")
    return ApplicationStrategy.model_validate(payload["application_strategy"])


def resolve_strategy(*, job_file: Path | None, strategy_json: Path | None) -> tuple[ApplicationStrategy, str]:
    if strategy_json is not None:
        path = strategy_json.resolve()
        return load_strategy_from_pipeline_json(path), str(path)
    if job_file is not None:
        candidate = _MANUAL_OUTPUTS / f"{job_file.stem}.json"
        if candidate.is_file():
            return load_strategy_from_pipeline_json(candidate), str(candidate.resolve())
        raise SystemExit(
            f"No pipeline JSON at {candidate}. Run "
            f"`python scripts/run_application_strategy_manual.py --job-file {job_file}` "
            "first (writes manual_validation/outputs/{stem}.json), or pass --strategy-json."
        )
    raise SystemExit("Provide --job-file or --strategy-json.")


def load_profile(profile_path: Path | None) -> CareerProfile:
    service = (
        CareerProfileService.from_path(profile_path)
        if profile_path is not None
        else CareerProfileService()
    )
    return service.load()


def run(
    *,
    job_file: Path | None,
    strategy_json: Path | None,
    profile_path: Path | None,
    output_dir: Path | None,
    owner_approved_to_plan: bool,
    cover_letter_plan_approved: bool,
    override_material_benefit: bool,
    plan_only: bool,
) -> RunResult:
    profile = load_profile(profile_path)
    strategy, source = resolve_strategy(job_file=job_file, strategy_json=strategy_json)
    print(f"Upstream strategy: {source}")
    print(f"application_tier: {strategy.application_tier}")
    print(f"pursuit_posture: {strategy.pursuit_posture}")
    print(f"company: {strategy.job_analysis.posting.company}")
    print(f"title: {strategy.job_analysis.posting.title}")

    plan_service = CoverLetterPlanService(DeterministicCoverLetterPlanner())
    try:
        plan = plan_service.plan(
            strategy,
            profile,
            options=CoverLetterPlanOptions(
                owner_approved_to_plan=owner_approved_to_plan,
                override_material_benefit=override_material_benefit,
            ),
        )
    except CoverLetterPlanGateError as exc:
        return RunResult(
            strategy=strategy,
            plan=None,
            letter=None,
            gate_message=str(exc),
            override_material_benefit=override_material_benefit,
            output_dir=None,
            stem=None,
            markdown_path=None,
            html_path=None,
        )

    if plan_only or not cover_letter_plan_approved:
        return RunResult(
            strategy=strategy,
            plan=plan,
            letter=None,
            gate_message=None,
            override_material_benefit=override_material_benefit,
            output_dir=None,
            stem=None,
            markdown_path=None,
            html_path=None,
        )

    letter = CoverLetterGenerationService().generate(
        strategy,
        profile,
        plan,
        options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=_DEFAULT_CONTACT,
        ),
    )
    out = output_dir or default_generated_dir(_REPO_ROOT)
    drafts = write_cover_letter_drafts(letter, plan, output_dir=out)
    return RunResult(
        strategy=strategy,
        plan=plan,
        letter=letter,
        gate_message=None,
        override_material_benefit=override_material_benefit,
        output_dir=drafts.output_dir,
        stem=drafts.stem,
        markdown_path=drafts.markdown_path,
        html_path=drafts.html_path,
    )


def format_report(result: RunResult) -> str:
    lines = [
        "=" * 72,
        "Career Intelligence Copilot - FR-007 Cover Letter Manual Validation",
        "=" * 72,
        "",
        "Validate in three steps:",
        "  Q1. Is the CoverLetterPlan grounded (company / role / evidence / projects)?",
        "  Q2. Does the letter read as authentic narrative (no planner jargon)?",
        "  Q3. Do Markdown + HTML look like the same suite as the tailored CV?",
        "",
    ]
    if result.gate_message:
        lines.extend(
            [
                "FR-007 gates",
                "-" * 40,
                f"  material_benefit_allows: {material_benefit_allows(result.strategy)}",
                f"  override_material_benefit: {result.override_material_benefit}",
                f"  gate_message: {result.gate_message}",
                "",
                "Cover Letter Plan: (not produced)",
                "",
            ]
        )
        return "\n".join(lines)

    assert result.plan is not None
    plan = result.plan
    lines.extend(
        [
            "Cover Letter Plan (Q1)",
            "-" * 40,
            f"  company: {plan.company_alignment.company}",
            f"  alignment_hook: {plan.company_alignment.alignment_hook}",
            f"  role: {plan.role_motivation.role_title}",
            f"  motivation: {plan.role_motivation.motivation}",
            f"  evidence_points: {len(plan.relevant_evidence)}",
            f"  strongest_projects: {[p.project_id for p in plan.strongest_projects]}",
            f"  closing: {plan.closing_strategy.approach}",
            f"  insufficient_evidence: {plan.insufficient_evidence}",
            "",
        ]
    )
    if result.letter is None:
        lines.append("Cover Letter: (plan only)")
        lines.append("")
        return "\n".join(lines)

    letter = result.letter
    lines.extend(
        [
            "Cover Letter (Q2)",
            "-" * 40,
            f"  owner_review_required: {letter.owner_review_required}",
            f"  composition_source: {letter.composition_source}",
            f"  paragraphs: {len(letter.paragraphs)}",
            "",
            "Draft outputs (visual regression: review MD + HTML together)",
            "-" * 40,
            f"  output_dir: {result.output_dir}",
            f"  stem: {result.stem}",
            f"  markdown: {result.markdown_path}",
            f"  html: {result.html_path}",
            "",
            "Preview (Markdown)",
            "-" * 40,
            letter.rendered_markdown.rstrip(),
            "",
            "Reminder: do not submit or email without owner review.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(
        job_file=args.job_file,
        strategy_json=args.strategy_json,
        profile_path=args.profile_path,
        output_dir=args.output_dir,
        owner_approved_to_plan=not args.not_owner_approved_to_plan,
        cover_letter_plan_approved=not args.not_cover_letter_plan_approved,
        override_material_benefit=args.override_material_benefit,
        plan_only=args.plan_only,
    )
    print(format_report(result))
    return 0 if result.gate_message is None else 2


if __name__ == "__main__":
    sys.exit(main())
