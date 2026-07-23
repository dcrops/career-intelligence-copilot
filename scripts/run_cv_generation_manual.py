#!/usr/bin/env python3
"""Manual validation runner for FR-006 (Tailoring Plan + Tailored CV).

Upstream (FR-001→FR-005) resolution order:

1. ``--strategy-json PATH`` — reuse a saved FR-005 pipeline JSON
   (e.g. ``manual_validation/outputs/013_….json``).
2. Auto-reuse — when ``--job-file`` stem matches
   ``manual_validation/outputs/{stem}.json`` (unless ``--live-upstream``).
3. ``--offline-fixtures`` — FixtureExtractor/Assessor smoke only for texts that
   contain a recognised ``[CIC-FIXTURE:…]`` marker. Not for real SEEK/LinkedIn ads.
4. Live OpenAI upstream — requires ``OPENAI_API_KEY``.

FR-006 Tailoring Plan and CV render are deterministic. Phase C summary rewrite is
opt-in via ``--rewrite-summary`` (OpenAI) and remains off by default.

Examples:
  # Preferred: reuse FR-005 manual validation artefacts (deterministic)
  python scripts/run_cv_generation_manual.py \\
    --job-file manual_validation/jobs/013_pay_com_au_ai_automation_engineer.txt

  python scripts/run_cv_generation_manual.py \\
    --strategy-json manual_validation/outputs/013_pay_com_au_ai_automation_engineer.json

  # Phase C opt-in summary rewrite (requires OPENAI_API_KEY)
  python scripts/run_cv_generation_manual.py \\
    --job-file manual_validation/jobs/002_bluefin_ai_systems_developer.txt \\
    --rewrite-summary

  # CIC-FIXTURE smoke only (not the FR-005 real-job corpus)
  python scripts/run_cv_generation_manual.py --job-file fixture.txt --offline-fixtures
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from career_intelligence.application_strategy import ApplicationStrategy
from career_intelligence.cv_generation import (
    CvGenerationOptions,
    CvGenerationService,
    DeterministicTailoringPlanner,
    DraftWriteResult,
    TailoringOptions,
    TailoringPlan,
    TailoringPlanGateError,
    TailoringPlanService,
    default_generated_dir,
    write_tailored_cv_drafts,
)
from career_intelligence.cv_generation.draft_writer import build_draft_stem
from career_intelligence.cv_generation.models import TailoredCv
from career_intelligence.job_analysis.fixtures import FIXTURE_BUILDERS
from career_intelligence.profile import CareerProfile, CareerProfileService

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STRATEGY_SCRIPT = _REPO_ROOT / "scripts" / "run_application_strategy_manual.py"
_MANUAL_OUTPUTS = _REPO_ROOT / "manual_validation" / "outputs"


def _load_strategy_runner():
    spec = importlib.util.spec_from_file_location(
        "run_application_strategy_manual",
        _STRATEGY_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class ComponentMode:
    name: str
    implementation: str
    mode: str


@dataclass(frozen=True)
class CvPipelineResult:
    profile: CareerProfile
    strategy: ApplicationStrategy
    plan: TailoringPlan | None
    cv: TailoredCv | None
    drafts: DraftWriteResult | None
    tailoring_allowed: bool
    gate_message: str | None
    strategy_components: list[ComponentMode]
    upstream_mode: str
    upstream_source: str | None
    owner_approved_to_tailor: bool
    tailoring_plan_approved: bool
    include_extended_history: bool
    override_material_benefit: bool
    rewrite_summary: bool = False
    notes: tuple[str, ...] = ()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run FR-006 TailoringPlan + TailoredCv for owner manual validation. "
            "Reuses saved FR-005 pipeline JSON for the manual_validation corpus; "
            "--offline-fixtures is only for [CIC-FIXTURE:...] smoke texts."
        )
    )
    parser.add_argument(
        "--job-file",
        type=Path,
        help=(
            "UTF-8 job advertisement text. When the basename matches "
            "manual_validation/outputs/{stem}.json, that trusted upstream "
            "pipeline is reused by default."
        ),
    )
    parser.add_argument(
        "--strategy-json",
        type=Path,
        default=None,
        help=(
            "Path to a saved FR-005 pipeline JSON "
            "(must contain application_strategy). Skips live/fixture upstream."
        ),
    )
    parser.add_argument("--title", default=None)
    parser.add_argument("--company", default=None)
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--profile-path", type=Path, default=None)
    parser.add_argument(
        "--offline-fixtures",
        action="store_true",
        help=(
            "Upstream smoke only: FixtureExtractor + FixtureAssessor for job texts "
            "that contain a recognised [CIC-FIXTURE:...] marker. "
            "Do not use for real SEEK/LinkedIn ads in manual_validation/jobs/ - "
            "reuse saved outputs instead (default when a matching JSON exists)."
        ),
    )
    parser.add_argument(
        "--live-upstream",
        action="store_true",
        help=(
            "Force live FR-001->FR-005 (OpenAI for FR-002/003) even when a matching "
            "manual_validation/outputs JSON exists."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional OpenAI model override for live upstream stages only.",
    )
    parser.add_argument(
        "--volume-applications-enabled",
        action="store_true",
        help="Pass volume mode into Application Strategy (live/fixture upstream only).",
    )
    parser.add_argument(
        "--not-owner-approved-to-tailor",
        action="store_true",
        help="Refuse TailoringPlan generation (gate demonstration).",
    )
    parser.add_argument(
        "--not-tailoring-plan-approved",
        action="store_true",
        help="Stop after TailoringPlan; do not render TailoredCv.",
    )
    parser.add_argument(
        "--include-extended-history",
        action="store_true",
        help="Opt in to pre-Master-CV extended experience history.",
    )
    parser.add_argument(
        "--override-material-benefit",
        action="store_true",
        help="Recorded override of the platinum/gold / consider_cv_tailoring gate.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory for Markdown/JSON drafts "
            "(default: career-documents/cv/generated/)."
        ),
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Produce TailoringPlan and write plan JSON only (no TailoredCv).",
    )
    parser.add_argument(
        "--rewrite-summary",
        action="store_true",
        help=(
            "Opt into Phase C OpenAI summary rewrite (gpt-4o-mini). "
            "Requires OPENAI_API_KEY. Default remains profile summary copy. "
            "Failures fall back to the profile summary."
        ),
    )
    return parser


def material_benefit_allows(strategy: ApplicationStrategy) -> bool:
    if strategy.application_tier in {"platinum", "gold"}:
        return True
    return any(action.kind == "consider_cv_tailoring" for action in strategy.next_actions)


def posting_has_fixture_marker(raw_text: str) -> bool:
    return any(marker in raw_text for marker in FIXTURE_BUILDERS)


def find_manual_validation_pipeline_json(
    job_file: Path,
    *,
    repo_root: Path = _REPO_ROOT,
) -> Path | None:
    """Return manual_validation/outputs/{stem}.json when present."""
    candidate = repo_root / "manual_validation" / "outputs" / f"{job_file.stem}.json"
    if candidate.is_file():
        return candidate.resolve()
    return None


def load_strategy_from_pipeline_json(path: Path) -> ApplicationStrategy:
    """Load trusted ApplicationStrategy from an FR-005 manual runner JSON export."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Cannot read strategy JSON: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc

    if "application_strategy" not in payload:
        raise SystemExit(
            f"Pipeline JSON missing 'application_strategy': {path}. "
            "Pass an FR-005 manual validation output "
            "(scripts/run_application_strategy_manual.py --output-json …)."
        )
    try:
        return ApplicationStrategy.model_validate(payload["application_strategy"])
    except Exception as exc:
        raise SystemExit(
            f"application_strategy in {path} failed validation: {exc}"
        ) from exc


def load_profile(profile_path: Path | None) -> CareerProfile:
    service = (
        CareerProfileService.from_path(profile_path)
        if profile_path is not None
        else CareerProfileService()
    )
    return service.load()


def resolve_upstream(
    *,
    job_file: Path | None,
    strategy_json: Path | None,
    posting: Any | None,
    profile_path: Path | None,
    volume_applications_enabled: bool,
    offline_fixtures: bool,
    live_upstream: bool,
    model: str | None,
    repo_root: Path = _REPO_ROOT,
) -> tuple[CareerProfile, ApplicationStrategy, list[ComponentMode], str, str | None, tuple[str, ...]]:
    """Resolve profile + trusted ApplicationStrategy for FR-006.

    Returns:
        profile, strategy, components, upstream_mode, upstream_source, notes
    """
    notes: list[str] = []
    profile = load_profile(profile_path)

    # 1) Explicit strategy JSON
    if strategy_json is not None:
        path = strategy_json.resolve()
        strategy = load_strategy_from_pipeline_json(path)
        components = [
            ComponentMode(
                "CareerProfile",
                "CareerProfileService / YAML",
                "deterministic_production",
            ),
            ComponentMode(
                "UpstreamPipeline",
                f"reused JSON ({path.name})",
                "reused_pipeline_json",
            ),
            ComponentMode(
                "ApplicationStrategy",
                "ApplicationStrategy from pipeline JSON",
                "reused_pipeline_json",
            ),
        ]
        return profile, strategy, components, "reused_pipeline_json", str(path), tuple(notes)

    if posting is None:
        raise SystemExit(
            "Provide --job-file / stdin job text, or --strategy-json for upstream reuse."
        )

    # 2) Auto-reuse manual_validation/outputs/{stem}.json from --job-file
    matched: Path | None = None
    if job_file is not None and not live_upstream:
        matched = find_manual_validation_pipeline_json(job_file, repo_root=repo_root)

    if matched is not None:
        if offline_fixtures:
            notes.append(
                "--offline-fixtures was ignored because this job is not a "
                "[CIC-FIXTURE:...] smoke text and a matching manual_validation "
                f"output exists ({matched.name}). Upstream artefacts were reused."
            )
        strategy = load_strategy_from_pipeline_json(matched)
        components = [
            ComponentMode(
                "CareerProfile",
                "CareerProfileService / YAML",
                "deterministic_production",
            ),
            ComponentMode(
                "UpstreamPipeline",
                f"reused JSON ({matched.name})",
                "reused_pipeline_json",
            ),
            ComponentMode(
                "ApplicationStrategy",
                "ApplicationStrategy from pipeline JSON",
                "reused_pipeline_json",
            ),
        ]
        return (
            profile,
            strategy,
            components,
            "reused_pipeline_json",
            str(matched),
            tuple(notes),
        )

    # 3) Offline fixtures — CIC-FIXTURE markers only
    if offline_fixtures:
        if not posting_has_fixture_marker(posting.raw_text):
            hint = ""
            if job_file is not None:
                expected = (
                    repo_root / "manual_validation" / "outputs" / f"{job_file.stem}.json"
                )
                hint = (
                    f"\nFor FR-005 corpus jobs, reuse saved artefacts, e.g.\n"
                    f"  python scripts/run_cv_generation_manual.py "
                    f"--job-file {job_file}\n"
                    f"or\n"
                    f"  python scripts/run_cv_generation_manual.py "
                    f"--strategy-json {expected}"
                )
            raise SystemExit(
                "--offline-fixtures requires a job text containing a recognised "
                "[CIC-FIXTURE:...] marker. Real SEEK/LinkedIn ads in "
                "manual_validation/jobs/ are not fixture texts."
                f"{hint}"
            )
        strategy_runner = _load_strategy_runner()
        strategy_result = strategy_runner.run_pipeline(
            posting=posting,
            profile_path=profile_path,
            volume_applications_enabled=volume_applications_enabled,
            offline_fixtures=True,
            model=model,
        )
        components = [
            ComponentMode(c.name, c.implementation, c.mode)
            for c in strategy_result.components
        ]
        return (
            strategy_result.profile,
            strategy_result.strategy,
            components,
            "offline_fixture",
            None,
            tuple(notes),
        )

    # 4) Live upstream
    strategy_runner = _load_strategy_runner()
    strategy_result = strategy_runner.run_pipeline(
        posting=posting,
        profile_path=profile_path,
        volume_applications_enabled=volume_applications_enabled,
        offline_fixtures=False,
        model=model,
    )
    components = [
        ComponentMode(c.name, c.implementation, c.mode)
        for c in strategy_result.components
    ]
    return (
        strategy_result.profile,
        strategy_result.strategy,
        components,
        "live_upstream",
        None,
        tuple(notes),
    )


def run_fr006_stages(
    *,
    profile: CareerProfile,
    strategy: ApplicationStrategy,
    strategy_components: list[ComponentMode],
    upstream_mode: str,
    upstream_source: str | None,
    owner_approved_to_tailor: bool,
    tailoring_plan_approved: bool,
    include_extended_history: bool,
    override_material_benefit: bool,
    output_dir: Path,
    plan_only: bool,
    rewrite_summary: bool = False,
    notes: tuple[str, ...] = (),
) -> CvPipelineResult:
    """Deterministic TailoringPlan -> TailoredCv; optional Phase C summary rewrite."""
    from career_intelligence.cv_generation.openai_summary_rewriter import (
        OpenAISummaryRewriter,
    )

    allowed = material_benefit_allows(strategy) or override_material_benefit

    def _result(
        *,
        plan_value: TailoringPlan | None = None,
        cv_value: TailoredCv | None = None,
        drafts_value: DraftWriteResult | None = None,
        gate: str | None = None,
        tailoring_ok: bool = allowed,
        note_extra: tuple[str, ...] = (),
    ) -> CvPipelineResult:
        return CvPipelineResult(
            profile=profile,
            strategy=strategy,
            plan=plan_value,
            cv=cv_value,
            drafts=drafts_value,
            tailoring_allowed=tailoring_ok,
            gate_message=gate,
            strategy_components=strategy_components,
            upstream_mode=upstream_mode,
            upstream_source=upstream_source,
            owner_approved_to_tailor=owner_approved_to_tailor,
            tailoring_plan_approved=tailoring_plan_approved,
            include_extended_history=include_extended_history,
            override_material_benefit=override_material_benefit,
            rewrite_summary=rewrite_summary,
            notes=notes + note_extra,
        )

    if not owner_approved_to_tailor:
        return _result(
            gate="owner_approved_to_tailor is False - TailoringPlan not produced."
        )

    try:
        plan = TailoringPlanService(DeterministicTailoringPlanner()).plan(
            strategy,
            profile,
            options=TailoringOptions(
                owner_approved_to_tailor=True,
                include_extended_history=include_extended_history,
                override_material_benefit=override_material_benefit,
            ),
        )
    except TailoringPlanGateError as exc:
        return _result(gate=str(exc), tailoring_ok=False)

    if plan_only or not tailoring_plan_approved:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = build_draft_stem(
            company=strategy.job_analysis.posting.company,
            title=strategy.job_analysis.posting.title,
        )
        plan_path = output_dir / f"{stem}.tailoring_plan.json"
        plan_path.write_text(
            json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        drafts = DraftWriteResult(
            output_dir=output_dir,
            stem=stem,
            markdown_path=output_dir / f"{stem}.md",
            json_path=output_dir / f"{stem}.json",
            plan_json_path=plan_path,
        )
        gate = None
        if not tailoring_plan_approved:
            gate = (
                "tailoring_plan_approved is False - TailoredCv not rendered. "
                f"Plan JSON written to {plan_path}"
            )
        return _result(plan_value=plan, drafts_value=drafts, gate=gate)

    rewriter = None
    note_extra: tuple[str, ...] = ()
    if rewrite_summary:
        _prepare_openai_runtime_for_summary_rewrite()
        rewriter = OpenAISummaryRewriter()
        note_extra = (
            "Phase C rewrite_summary enabled (OpenAISummaryRewriter; "
            "truststore SSL path aligned with FR-002/003 manual runners).",
        )
    cv = CvGenerationService(rewriter).generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            rewrite_summary=rewrite_summary,
        ),
    )
    drafts = write_tailored_cv_drafts(cv, plan, output_dir=output_dir)
    return _result(
        plan_value=plan,
        cv_value=cv,
        drafts_value=drafts,
        note_extra=note_extra,
    )


def _prepare_openai_runtime_for_summary_rewrite() -> None:
    """Match FR-002/003 live manual path: require API key + Windows SSL truststore.

    Corpus FR-006 runs reuse saved strategy JSON and therefore never enter
    ``run_application_strategy_manual``'s live OpenAI branch. Phase C must
    apply the same ``truststore.inject_into_ssl()`` preparation here or the
    first OpenAI call fails with a generic connection error on Windows.
    """
    import os

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Phase C --rewrite-summary requires OpenAI."
        )
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        # Optional where system certs already work (same as strategy runner).
        pass


def run_cv_pipeline(
    *,
    posting: Any | None = None,
    job_file: Path | None = None,
    strategy_json: Path | None = None,
    profile_path: Path | None = None,
    volume_applications_enabled: bool = False,
    offline_fixtures: bool = False,
    live_upstream: bool = False,
    model: str | None = None,
    owner_approved_to_tailor: bool = True,
    tailoring_plan_approved: bool = True,
    include_extended_history: bool = False,
    override_material_benefit: bool = False,
    output_dir: Path,
    plan_only: bool = False,
    rewrite_summary: bool = False,
    repo_root: Path = _REPO_ROOT,
) -> CvPipelineResult:
    """Resolve upstream then run deterministic FR-006 stages."""
    profile, strategy, components, mode, source, notes = resolve_upstream(
        job_file=job_file,
        strategy_json=strategy_json,
        posting=posting,
        profile_path=profile_path,
        volume_applications_enabled=volume_applications_enabled,
        offline_fixtures=offline_fixtures,
        live_upstream=live_upstream,
        model=model,
        repo_root=repo_root,
    )
    return run_fr006_stages(
        profile=profile,
        strategy=strategy,
        strategy_components=components,
        upstream_mode=mode,
        upstream_source=source,
        owner_approved_to_tailor=owner_approved_to_tailor,
        tailoring_plan_approved=tailoring_plan_approved,
        include_extended_history=include_extended_history,
        override_material_benefit=override_material_benefit,
        output_dir=output_dir,
        plan_only=plan_only,
        rewrite_summary=rewrite_summary,
        notes=notes,
    )


def format_report(result: CvPipelineResult) -> str:
    strategy = result.strategy
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("Career Intelligence Copilot - FR-006 CV Generation Manual Validation")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Validate in two steps:")
    lines.append("  Q1. Is the Tailoring Plan correct for this JD?")
    lines.append("  Q2. Does the Tailored CV faithfully render that plan?")
    lines.append("")

    lines.append("Upstream component modes")
    lines.append("-" * 72)
    lines.append(f"  upstream_mode: {result.upstream_mode}")
    if result.upstream_source:
        lines.append(f"  upstream_source: {result.upstream_source}")
    for component in result.strategy_components:
        lines.append(
            f"  {component.name}: {component.implementation} [{component.mode}]"
        )
    if result.upstream_mode == "offline_fixture":
        lines.append("")
        lines.append(
            "WARNING: offline fixture mode is for [CIC-FIXTURE:...] smoke tests only - "
            "not the FR-005 real-job corpus."
        )
    if result.upstream_mode == "reused_pipeline_json":
        lines.append("")
        lines.append(
            "NOTE: FR-001->FR-005 artefacts were reused from saved pipeline JSON. "
            "FR-006 stages below are deterministic."
        )
    for note in result.notes:
        lines.append("")
        lines.append(f"NOTE: {note}")
    lines.append("")

    lines.append("Application strategy (inputs to FR-006)")
    lines.append("-" * 72)
    lines.append(f"  application_tier: {strategy.application_tier}")
    lines.append(f"  pursuit_posture: {strategy.pursuit_posture}")
    lines.append(f"  effort_level: {strategy.effort_level}")
    lines.append(
        f"  consider_cv_tailoring: "
        f"{any(a.kind == 'consider_cv_tailoring' for a in strategy.next_actions)}"
    )
    lines.append("")

    lines.append("FR-006 gates")
    lines.append("-" * 72)
    lines.append(f"  owner_approved_to_tailor: {result.owner_approved_to_tailor}")
    lines.append(f"  material_benefit_allows: {material_benefit_allows(strategy)}")
    lines.append(f"  override_material_benefit: {result.override_material_benefit}")
    lines.append(f"  tailoring_allowed: {result.tailoring_allowed}")
    lines.append(f"  tailoring_plan_approved: {result.tailoring_plan_approved}")
    lines.append(f"  include_extended_history: {result.include_extended_history}")
    if result.gate_message:
        lines.append(f"  gate_message: {result.gate_message}")
    lines.append("")

    if result.plan is None:
        lines.append("Tailoring Plan: (not produced)")
        lines.append("")
        lines.append(
            "Reminder: owner review is required before any external application action."
        )
        return "\n".join(lines)

    plan = result.plan
    lines.append("Tailoring Plan (Q1 - review against the JD)")
    lines.append("-" * 72)
    lines.append(f"  insufficient_evidence: {plan.insufficient_evidence}")
    lines.append(f"  owner_review_recommended: {plan.owner_review_recommended}")
    lines.append(f"  experience_guidance: {plan.experience_guidance.kind}")
    lines.append(
        f"  included_experience_ids: {len(plan.experience_guidance.included_experience_ids)}"
    )
    lines.append(
        f"  excluded_experience_ids: {len(plan.experience_guidance.excluded_experience_ids)}"
    )
    lines.append("")

    lines.append("  Top JD priorities:")
    if plan.jd_priorities:
        for item in plan.jd_priorities:
            related = (
                f" -> {item.related_profile_capability}"
                if item.related_profile_capability
                else ""
            )
            lines.append(
                f"    {item.rank}. [{item.kind}/{item.candidate_support}] "
                f"{item.label}{related}"
            )
            lines.append(f"       {item.rationale}")
    else:
        lines.append("    (none)")
    lines.append("")

    lines.append("  Projects promoted:")
    if plan.projects_to_emphasise:
        for item in plan.projects_to_emphasise:
            lines.append(f"    {item.rank}. {item.project_id}")
            lines.append(f"       {item.rationale}")
    else:
        lines.append("    (none)")
    lines.append("")

    lines.append("  Skills promoted:")
    if plan.skills_to_promote:
        for item in plan.skills_to_promote:
            lines.append(f"    {item.rank}. {item.skill_name} ({item.category})")
    else:
        lines.append("    (none)")
    lines.append("")

    lines.append("  Skills not emphasised (retained, not removed):")
    if plan.skills_not_emphasised:
        for item in plan.skills_not_emphasised[:12]:
            lines.append(f"    - {item.skill_name} ({item.category})")
        if len(plan.skills_not_emphasised) > 12:
            lines.append(f"    - (+{len(plan.skills_not_emphasised) - 12} more)")
    else:
        lines.append("    (none)")
    lines.append("")

    lines.append("  Summary themes (Phase C will rewrite prose against these):")
    if plan.summary_themes:
        for item in plan.summary_themes:
            lines.append(f"    {item.rank}. {item.theme}")
    else:
        lines.append("    (none)")
    lines.append("")

    if plan.assumptions:
        lines.append("  Plan assumptions:")
        for item in plan.assumptions:
            lines.append(f"    - {item}")
        lines.append("")

    if result.cv is None:
        lines.append("Tailored CV: (not rendered)")
    else:
        cv = result.cv
        lines.append("Tailored CV (Q2 - confirm faithful render of the plan)")
        lines.append("-" * 72)
        lines.append(f"  owner_review_required: {cv.owner_review_required}")
        lines.append(f"  summary_source: {cv.summary_source}")
        lines.append(f"  certifications_source: {cv.certifications_source}")
        lines.append(
            f"  emphasised_skills: {[s.skill_name for s in cv.skills if s.emphasised]}"
        )
        lines.append(f"  project_order: {[p.project_id for p in cv.projects]}")
        lines.append(f"  experience_ids: {[e.experience_id for e in cv.experience]}")
        lines.append("")

    if result.drafts is not None:
        lines.append("Draft outputs")
        lines.append("-" * 72)
        lines.append(f"  output_dir: {result.drafts.output_dir}")
        lines.append(f"  stem: {result.drafts.stem}")
        lines.append(f"  plan_json: {result.drafts.plan_json_path}")
        if result.cv is not None:
            lines.append(f"  markdown: {result.drafts.markdown_path}")
            lines.append(f"  cv_json: {result.drafts.json_path}")
        lines.append("")

    lines.append(
        "Reminder: drafts must not be submitted or emailed without owner review. "
        "Phase C summary rewrite is opt-in via --rewrite-summary "
        f"(enabled={result.rewrite_summary})."
    )
    return "\n".join(lines)


def read_job_text(job_file: Path | None, stdin: TextIO = sys.stdin) -> str:
    return _load_strategy_runner().read_job_text(job_file, stdin=stdin)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    strategy_runner = _load_strategy_runner()

    owner_approved = True
    if args.not_owner_approved_to_tailor:
        owner_approved = False
    plan_approved = True
    if args.not_tailoring_plan_approved or args.plan_only:
        plan_approved = False

    output_dir = args.output_dir or default_generated_dir(_REPO_ROOT)

    try:
        posting = None
        # Job text is required unless --strategy-json alone supplies upstream.
        if args.job_file is not None or args.strategy_json is None:
            raw_text = read_job_text(args.job_file)
            posting = strategy_runner.build_posting(
                raw_text,
                title=args.title,
                company=args.company,
                source_url=args.source_url,
            )

        result = run_cv_pipeline(
            posting=posting,
            job_file=args.job_file,
            strategy_json=args.strategy_json,
            profile_path=args.profile_path,
            volume_applications_enabled=args.volume_applications_enabled,
            offline_fixtures=args.offline_fixtures,
            live_upstream=args.live_upstream,
            model=args.model,
            owner_approved_to_tailor=owner_approved,
            tailoring_plan_approved=plan_approved,
            include_extended_history=args.include_extended_history,
            override_material_benefit=args.override_material_benefit,
            output_dir=output_dir,
            plan_only=args.plan_only,
            rewrite_summary=args.rewrite_summary,
        )
    except SystemExit:
        raise
    except Exception as exc:
        print(strategy_runner._format_pipeline_failure(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
