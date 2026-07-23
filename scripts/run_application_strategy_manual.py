#!/usr/bin/env python3
"""Manual validation runner for FR-001 -> FR-005 on a real job advertisement.

Default path (live / owner validation):
  CareerProfileService
  -> JobAnalysisService(OpenAIJobExtractor)
  -> OpportunityAssessmentService(OpenAIAssessor)
  -> PortfolioMatchingService(DeterministicMatcher)
  -> ApplicationStrategyService(DeterministicStrategyPlanner)

Offline smoke requires an explicit ``--offline-fixtures`` flag and is clearly
labelled as non-production. Fixture behaviour is never substituted silently.

Examples:
  python scripts/run_application_strategy_manual.py --job-file path/to/job.txt
  Get-Content job.txt | python scripts/run_application_strategy_manual.py
  python scripts/run_application_strategy_manual.py --job-file job.txt --volume-applications-enabled
  python scripts/run_application_strategy_manual.py --job-file job.txt --output-json out.json
  python scripts/run_application_strategy_manual.py --job-file job.txt --offline-fixtures --persist
  python scripts/run_application_strategy_manual.py --job-file tests/.../fixture.txt --offline-fixtures
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from career_intelligence.application_strategy import (
    ApplicationStrategy,
    ApplicationStrategyService,
    SearchOperatingContext,
)
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.job_analysis import JobAnalysis, JobAnalysisService, JobPosting
from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor
from career_intelligence.opportunities import Opportunity, OpportunityService
from career_intelligence.opportunity_assessment import (
    OpportunityAssessment,
    OpportunityAssessmentService,
)
from career_intelligence.opportunity_assessment.openai_assessor import OpenAIAssessor
from career_intelligence.portfolio_matching import PortfolioMatch, PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.profile import CareerProfile, CareerProfileService

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ComponentMode:
    name: str
    implementation: str
    mode: str  # "openai_production" | "deterministic_production" | "offline_fixture"


@dataclass(frozen=True)
class PipelineResult:
    profile: CareerProfile
    posting: JobPosting
    job_analysis: JobAnalysis
    assessment: OpportunityAssessment
    portfolio_match: PortfolioMatch
    strategy: ApplicationStrategy
    components: list[ComponentMode]
    volume_applications_enabled: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run CareerProfile -> JobAnalysis -> OpportunityAssessment -> "
            "PortfolioMatch -> ApplicationStrategy for owner manual validation."
        )
    )
    parser.add_argument(
        "--job-file",
        type=Path,
        help="Path to a UTF-8 text file containing the job advertisement body.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional job title provenance for JobPosting.",
    )
    parser.add_argument(
        "--company",
        default=None,
        help="Optional company provenance for JobPosting.",
    )
    parser.add_argument(
        "--source-url",
        default=None,
        help="Optional source URL provenance for JobPosting.",
    )
    parser.add_argument(
        "--profile-path",
        type=Path,
        default=None,
        help="Override career profile path (else CIC_PROFILE_PATH or data/career_profile.yaml).",
    )
    parser.add_argument(
        "--volume-applications-enabled",
        action="store_true",
        help="Set SearchOperatingContext.volume_applications_enabled=True.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to write the full typed pipeline result as JSON.",
    )
    parser.add_argument(
        "--offline-fixtures",
        action="store_true",
        help=(
            "Explicit offline smoke mode using FixtureExtractor + FixtureAssessor. "
            "Not for live owner validation. Requires a recognised CIC-FIXTURE marker "
            "in the job text."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional OpenAI model override for extractor and assessor (live mode only).",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help=(
            "Persist FR-002–FR-005 artifacts as a durable Opportunity "
            "(immutable snapshots under data/opportunities/)."
        ),
    )
    parser.add_argument(
        "--opportunities-dir",
        type=Path,
        default=None,
        help="Override opportunities store directory (used with --persist).",
    )
    return parser


def read_job_text(job_file: Path | None, stdin: TextIO = sys.stdin) -> str:
    if job_file is not None:
        text = job_file.read_text(encoding="utf-8").strip()
        if not text:
            raise SystemExit(f"Job file is empty: {job_file}")
        return text
    if stdin.isatty():
        raise SystemExit(
            "No --job-file provided and stdin is a terminal. "
            "Pass --job-file PATH or pipe job text into stdin."
        )
    text = stdin.read().strip()
    if not text:
        raise SystemExit("Stdin job text is empty.")
    return text


def build_posting(
    raw_text: str,
    *,
    title: str | None,
    company: str | None,
    source_url: str | None,
) -> JobPosting:
    payload: dict[str, Any] = {"raw_text": raw_text}
    if title:
        payload["title"] = title
    if company:
        payload["company"] = company
    if source_url:
        payload["source_url"] = source_url
    return JobPosting.model_validate(payload)


def _require_openai_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Live manual validation requires OpenAI for "
            "Job Analysis and Opportunity Assessment. For an explicit offline smoke "
            "test only, pass --offline-fixtures with a CIC-FIXTURE marked job text."
        )


def run_pipeline(
    *,
    posting: JobPosting,
    profile_path: Path | None,
    volume_applications_enabled: bool,
    offline_fixtures: bool,
    model: str | None,
) -> PipelineResult:
    profile_service = (
        CareerProfileService.from_path(profile_path)
        if profile_path is not None
        else CareerProfileService()
    )
    profile = profile_service.load()

    if offline_fixtures:
        from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
        from career_intelligence.opportunity_assessment.fixture_assessor import (
            FixtureAssessor,
        )

        job_service = JobAnalysisService(FixtureExtractor())
        assessment_service = OpportunityAssessmentService(FixtureAssessor())
        components = [
            ComponentMode("CareerProfile", "CareerProfileService / YAML", "deterministic_production"),
            ComponentMode(
                "JobAnalysis",
                "FixtureExtractor",
                "offline_fixture",
            ),
            ComponentMode(
                "OpportunityAssessment",
                "FixtureAssessor",
                "offline_fixture",
            ),
            ComponentMode(
                "PortfolioMatch",
                "DeterministicMatcher",
                "deterministic_production",
            ),
            ComponentMode(
                "ApplicationStrategy",
                "DeterministicStrategyPlanner",
                "deterministic_production",
            ),
        ]
    else:
        _require_openai_key()
        try:
            import truststore

            truststore.inject_into_ssl()
        except ImportError:
            # Optional on environments where system certs already work.
            pass
        extractor_kwargs: dict[str, Any] = {}
        assessor_kwargs: dict[str, Any] = {}
        if model is not None:
            extractor_kwargs["model"] = model
            assessor_kwargs["model"] = model
        job_service = JobAnalysisService(OpenAIJobExtractor(**extractor_kwargs))
        assessment_service = OpportunityAssessmentService(OpenAIAssessor(**assessor_kwargs))
        components = [
            ComponentMode("CareerProfile", "CareerProfileService / YAML", "deterministic_production"),
            ComponentMode("JobAnalysis", "OpenAIJobExtractor", "openai_production"),
            ComponentMode("OpportunityAssessment", "OpenAIAssessor", "openai_production"),
            ComponentMode(
                "PortfolioMatch",
                "DeterministicMatcher",
                "deterministic_production",
            ),
            ComponentMode(
                "ApplicationStrategy",
                "DeterministicStrategyPlanner",
                "deterministic_production",
            ),
        ]

    job_analysis = job_service.analyse(posting)
    assessment = assessment_service.assess(job_analysis, profile)
    portfolio_match = PortfolioMatchingService(DeterministicMatcher()).match(
        job_analysis, profile
    )
    strategy = ApplicationStrategyService(DeterministicStrategyPlanner()).plan(
        assessment,
        portfolio_match,
        profile,
        operating_context=SearchOperatingContext(
            volume_applications_enabled=volume_applications_enabled
        ),
    )

    return PipelineResult(
        profile=profile,
        posting=posting,
        job_analysis=job_analysis,
        assessment=assessment,
        portfolio_match=portfolio_match,
        strategy=strategy,
        components=components,
        volume_applications_enabled=volume_applications_enabled,
    )


def _truncate(text: str, limit: int = 160) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def format_report(result: PipelineResult) -> str:
    strategy = result.strategy
    assessment = result.assessment
    match = result.portfolio_match
    analysis = result.job_analysis
    lines: list[str] = []

    lines.append("=" * 72)
    lines.append("Career Intelligence Copilot - Application Strategy Manual Validation")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Component modes")
    lines.append("-" * 72)
    for component in result.components:
        lines.append(
            f"  {component.name}: {component.implementation} [{component.mode}]"
        )
    if any(item.mode == "offline_fixture" for item in result.components):
        lines.append("")
        lines.append(
            "WARNING: offline fixture mode is for smoke tests only - not live owner validation."
        )
    lines.append("")
    lines.append(
        f"volume_applications_enabled: {result.volume_applications_enabled}"
    )
    lines.append(f"owner_review_required: {strategy.owner_review_required}")
    lines.append("")

    lines.append("Job identity")
    lines.append("-" * 72)
    lines.append(f"  title: {result.posting.title or '(unset)'}")
    lines.append(f"  company: {result.posting.company or '(unset)'}")
    lines.append(f"  source_url: {result.posting.source_url or '(unset)'}")
    lines.append(f"  raw_text_chars: {len(result.posting.raw_text)}")
    lines.append("")

    lines.append("Job analysis summary")
    lines.append("-" * 72)
    lines.append(f"  role_family: {analysis.role_family.family}")
    lines.append(
        f"  seniority: {analysis.seniority.level}"
        + (" (ambiguous)" if analysis.seniority.ambiguous else "")
    )
    tech_names = ", ".join(item.name for item in analysis.technologies[:8]) or "(none)"
    lines.append(f"  technologies: {tech_names}")
    lines.append(f"  responsibilities: {len(analysis.responsibilities)}")
    lines.append(f"  compensation.clarity: {analysis.compensation.clarity}")
    lines.append(
        f"  location: {analysis.location.summary or analysis.location.clarity}"
    )
    lines.append(
        f"  work_arrangement: {analysis.work_arrangement.arrangement}"
    )
    lines.append(
        "  employment: "
        f"{analysis.employment.working_hours} / {analysis.employment.engagement_type}"
    )
    lines.append("")

    lines.append("Opportunity assessment")
    lines.append("-" * 72)
    lines.append(f"  technical_fit: {assessment.technical_fit.judgment}")
    lines.append(f"  commercial_fit: {assessment.commercial_fit.judgment}")
    lines.append(f"  portfolio_fit: {assessment.portfolio_fit.judgment}")
    lines.append(f"  summary: {_truncate(assessment.summary.summary)}")
    lines.append("")

    lines.append("Portfolio match")
    lines.append("-" * 72)
    lines.append(f"  insufficient_evidence: {match.insufficient_evidence}")
    lines.append(f"  summary: {_truncate(match.summary)}")
    if match.ranked_projects:
        for entry in match.ranked_projects[:5]:
            lines.append(f"  #{entry.rank} {entry.project_id} - {_truncate(entry.rationale, 100)}")
    else:
        lines.append("  ranked_projects: (none)")
    lines.append("")

    lines.append("Application strategy")
    lines.append("-" * 72)
    lines.append(f"  pursuit_posture: {strategy.pursuit_posture}")
    lines.append(f"  application_tier: {strategy.application_tier}")
    lines.append(f"  practical_value: {strategy.practical_value}")
    lines.append(f"  effort_level: {strategy.effort_level}")
    lines.append(f"  insufficient_information: {strategy.insufficient_information}")
    lines.append(f"  summary: {strategy.summary}")
    lines.append("")

    lines.append("Reasons")
    lines.append("-" * 72)
    for index, reason in enumerate(strategy.reasons, start=1):
        lines.append(f"  {index}. [{reason.kind}/{reason.importance}] {reason.summary}")
        for evidence in reason.evidence:
            lines.append(f"      evidence: {_format_evidence(evidence)}")
    lines.append("")

    lines.append("Risks or gaps")
    lines.append("-" * 72)
    if strategy.risks_or_gaps:
        for index, risk in enumerate(strategy.risks_or_gaps, start=1):
            lines.append(f"  {index}. [{risk.importance}] {risk.summary}")
            for evidence in risk.evidence:
                lines.append(f"      evidence: {_format_evidence(evidence)}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Decision blockers")
    lines.append("-" * 72)
    if strategy.decision_blockers:
        for item in strategy.decision_blockers:
            lines.append(f"  - {item}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Manual checks")
    lines.append("-" * 72)
    if strategy.manual_checks:
        for index, check in enumerate(strategy.manual_checks, start=1):
            lines.append(
                f"  {index}. {check.summary} "
                f"(could_change_recommendation={check.could_change_recommendation})"
            )
            lines.append(f"      why: {check.why_it_matters}")
            for evidence in check.evidence:
                lines.append(f"      evidence: {_format_evidence(evidence)}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Assumptions")
    lines.append("-" * 72)
    if strategy.assumptions:
        for item in strategy.assumptions:
            lines.append(f"  - {item}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Portfolio emphasis")
    lines.append("-" * 72)
    if strategy.portfolio_emphasis:
        for entry in strategy.portfolio_emphasis:
            rank = entry.source_rank if entry.source_rank is not None else "?"
            lines.append(f"  - rank {rank}: {entry.project_id} - {entry.summary}")
            for evidence in entry.evidence:
                lines.append(f"      evidence: {_format_evidence(evidence)}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Next actions")
    lines.append("-" * 72)
    for index, action in enumerate(strategy.next_actions, start=1):
        related = (
            f" (project={action.related_project_id})"
            if action.related_project_id
            else ""
        )
        lines.append(f"  {index}. {action.kind}{related}")
        lines.append(f"      {action.summary}")
        for evidence in action.evidence:
            lines.append(f"      evidence: {_format_evidence(evidence)}")
    lines.append("")
    lines.append(
        "Reminder: this is decision support only. Owner review is required before any "
        "external application action."
    )
    return "\n".join(lines)


def _format_evidence(evidence: Any) -> str:
    origin = evidence.origin
    if origin == "job_analysis" and evidence.job_evidence is not None:
        ref = evidence.job_evidence
        parts = [ref.source]
        if ref.item_index is not None:
            parts.append(f"index={ref.item_index}")
        if ref.name:
            parts.append(f"name={ref.name}")
        return f"{origin} ({', '.join(parts)})"
    if origin == "career_profile" and evidence.profile_evidence is not None:
        pe = evidence.profile_evidence
        # Profile refs already use namespace:id (e.g. preference:locations).
        if pe.ref.startswith(f"{pe.source}:"):
            return f"{origin} ({pe.ref})"
        return f"{origin} ({pe.source}:{pe.ref})"
    if origin == "opportunity_assessment":
        judgment = evidence.assessment_judgment or "?"
        return f"{origin} ({evidence.assessment_dimension}={judgment})"
    if origin == "portfolio_match":
        return f"{origin} (project={evidence.portfolio_project_id})"
    return origin


def pipeline_to_jsonable(result: PipelineResult) -> dict[str, Any]:
    return {
        "components": [
            {
                "name": item.name,
                "implementation": item.implementation,
                "mode": item.mode,
            }
            for item in result.components
        ],
        "volume_applications_enabled": result.volume_applications_enabled,
        "profile_identity": {
            "full_name": result.profile.identity.full_name,
            "target_role": result.profile.identity.target_role,
        },
        "posting": result.posting.model_dump(mode="json"),
        "job_analysis": result.job_analysis.model_dump(mode="json"),
        "opportunity_assessment": result.assessment.model_dump(mode="json"),
        "portfolio_match": result.portfolio_match.model_dump(mode="json"),
        "application_strategy": result.strategy.model_dump(mode="json"),
    }


def write_json(path: Path, result: PipelineResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(pipeline_to_jsonable(result), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def persist_opportunity(
    result: PipelineResult,
    *,
    opportunities_dir: Path | None = None,
) -> Opportunity:
    """Persist trusted pipeline artifacts via OpportunityService (M1)."""
    service = (
        OpportunityService.from_path(opportunities_dir)
        if opportunities_dir is not None
        else OpportunityService()
    )
    return service.create_from_strategy(
        posting=result.posting,
        job_analysis=result.job_analysis,
        assessment=result.assessment,
        portfolio_match=result.portfolio_match,
        strategy=result.strategy,
    )


def _format_pipeline_failure(exc: BaseException) -> str:
    """Concise developer-facing failure summary for the manual runner."""
    component = _failure_component(exc)
    lines = [f"ERROR: {component} failed: {exc}"]

    details = getattr(exc, "errors", None)
    if isinstance(details, list) and details:
        lines.append("Validation details:")
        for item in details[:8]:
            loc = getattr(item, "loc", ())
            msg = getattr(item, "msg", str(item))
            loc_text = ".".join(str(part) for part in loc) if loc else "(root)"
            lines.append(f"  - {loc_text}: {msg}")
        if len(details) > 8:
            lines.append(f"  - (+{len(details) - 8} more)")
        return "\n".join(lines)

    cause = exc.__cause__
    if cause is not None and cause is not exc:
        lines.append(f"Caused by: {type(cause).__name__}: {cause}")
    return "\n".join(lines)


def _failure_component(exc: BaseException) -> str:
    name = type(exc).__name__
    if "JobAnalysis" in name:
        return "JobAnalysis"
    if "OpportunityAssessment" in name:
        return "OpportunityAssessment"
    if "PortfolioMatching" in name or "PortfolioMatch" in name:
        return "PortfolioMatch"
    if "ApplicationStrategy" in name:
        return "ApplicationStrategy"
    if "Opportunity" in name and "Assessment" not in name:
        return "OpportunityPersistence"
    if "Profile" in name:
        return "CareerProfile"
    return "Pipeline"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw_text = read_job_text(args.job_file)
        posting = build_posting(
            raw_text,
            title=args.title,
            company=args.company,
            source_url=args.source_url,
        )
        result = run_pipeline(
            posting=posting,
            profile_path=args.profile_path,
            volume_applications_enabled=args.volume_applications_enabled,
            offline_fixtures=args.offline_fixtures,
            model=args.model,
        )
    except SystemExit:
        raise
    except Exception as exc:
        print(_format_pipeline_failure(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    print(format_report(result))
    if args.output_json is not None:
        write_json(args.output_json, result)
        print(f"\nWrote JSON output to {args.output_json}")

    if args.persist:
        try:
            opportunity = persist_opportunity(
                result,
                opportunities_dir=args.opportunities_dir,
            )
        except Exception as exc:
            print(_format_pipeline_failure(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        store_root = args.opportunities_dir or (
            REPO_ROOT / "data" / "opportunities"
        )
        print("")
        print("Opportunity persisted (M1)")
        print("-" * 72)
        print(f"  opportunity_id: {opportunity.opportunity_id}")
        print(f"  status: {opportunity.status}")
        print(f"  store: {store_root}")
        print(f"  artifacts: {store_root / 'artifacts' / opportunity.opportunity_id}")
        for name, relative in sorted(opportunity.artifact_paths.items()):
            print(f"    - {name}: {relative}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
