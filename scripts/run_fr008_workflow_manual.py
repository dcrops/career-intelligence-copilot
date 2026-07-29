#!/usr/bin/env python3
"""Manual validation runner for FR-008 workflow orchestration.

Examples:
  # Paste path (file contents treated as pasted text)
  python scripts/run_fr008_workflow_manual.py start --source paste \\
      --job-file path/to/job.txt --offline-fixtures

  # Local export / file adapter
  python scripts/run_fr008_workflow_manual.py start --source export \\
      --job-file path/to/job.txt --offline-fixtures

  python scripts/run_fr008_workflow_manual.py resume --run-id wfr_... --decision apply --offline-fixtures
  python scripts/run_fr008_workflow_manual.py continue --run-id wfr_... --offline-fixtures
  python scripts/run_fr008_workflow_manual.py show --run-id wfr_...
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from career_intelligence.application_strategy import ApplicationStrategyService
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_assessment import OpportunityAssessmentService
from career_intelligence.orchestration import (
    ApplicationWorkflowRunner,
    FailureInjection,
    JsonDirectoryCheckpointStore,
    LocalFileAcquisitionAdapter,
    PasteJobInput,
    RetryPolicy,
    WorkflowDependencies,
    WorkflowState,
)
from career_intelligence.portfolio_matching import PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.profile import CareerProfileService

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT_DIR = REPO_ROOT / "data" / "workflow_runs"
DEFAULT_OPPORTUNITIES_DIR = REPO_ROOT / "data" / "opportunities"
SCRIPT = "scripts/run_fr008_workflow_manual.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FR-008 workflow manual validation (acquisition + orchestration)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--profile-path", type=Path, default=None)
        p.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
        p.add_argument(
            "--opportunities-dir",
            type=Path,
            default=DEFAULT_OPPORTUNITIES_DIR,
            help="Opportunity SoT directory (ADR-002)",
        )
        p.add_argument(
            "--offline-fixtures",
            action="store_true",
            help="Use FixtureExtractor/Assessor (requires CIC-FIXTURE marker)",
        )
        p.add_argument("--output-json", type=Path, default=None)
        p.add_argument(
            "--max-attempts",
            type=int,
            default=3,
            help="Retry budget for eligible nodes (default 3)",
        )

    def add_failure_injection(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--fail-node",
            choices=["analyse", "assess"],
            default=None,
            help="Inject bounded failures on this node (engineering validation)",
        )
        p.add_argument(
            "--fail-count",
            type=int,
            default=1,
            help="How many times the injected node fails before succeeding",
        )
        p.add_argument(
            "--failure-kind",
            choices=["recoverable", "unrecoverable"],
            default="recoverable",
            help="Classification for injected failures",
        )
        p.add_argument(
            "--yield-after-retry",
            action="store_true",
            help=(
                "Stop after scheduling a retry (cross-process demo). "
                "Resume with the continue command."
            ),
        )

    start = sub.add_parser("start", help="Run until owner-review interrupt / retry yield / fail")
    start.add_argument(
        "--source",
        choices=["paste", "export"],
        default="paste",
        help="Acquisition adapter: paste (file contents as pasted text) or export (local file)",
    )
    start.add_argument("--job-file", type=Path, required=True)
    start.add_argument("--title", default=None)
    start.add_argument("--company", default=None)
    start.add_argument("--source-url", default=None)
    add_common(start)
    add_failure_injection(start)

    cont = sub.add_parser(
        "continue",
        help="Continue a running checkpoint (retry recovery or mid-apply without new decision)",
    )
    cont.add_argument("--run-id", required=True)
    add_common(cont)
    add_failure_injection(cont)

    resume = sub.add_parser("resume", help="Resume an awaiting-owner / apply-recovery run")
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--decision", required=True, choices=["apply", "skip", "defer"])
    add_common(resume)

    reload_cmd = sub.add_parser(
        "reload",
        help="Re-invoke resume on a completed/in-progress run (idempotency check)",
    )
    reload_cmd.add_argument("--run-id", required=True)
    reload_cmd.add_argument("--decision", required=True, choices=["apply", "skip", "defer"])
    add_common(reload_cmd)

    show = sub.add_parser("show", help="Load checkpoint and optional Opportunity summary")
    show.add_argument("--run-id", required=True)
    show.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    show.add_argument("--opportunities-dir", type=Path, default=DEFAULT_OPPORTUNITIES_DIR)
    show.add_argument("--output-json", type=Path, default=None)

    return parser


def build_runner(
    *,
    checkpoint_dir: Path,
    opportunities_dir: Path,
    profile_path: Path | None,
    offline_fixtures: bool,
    max_attempts: int = 3,
    fail_node: str | None = None,
    fail_count: int = 1,
    failure_kind: str = "recoverable",
    yield_after_retry: bool = False,
) -> ApplicationWorkflowRunner:
    profile_service = (
        CareerProfileService.from_path(profile_path)
        if profile_path is not None
        else CareerProfileService()
    )
    profile = profile_service.load()
    store = JsonDirectoryCheckpointStore(checkpoint_dir)
    opportunities = OpportunityService.from_path(opportunities_dir)

    if offline_fixtures:
        from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
        from career_intelligence.opportunity_assessment.fixture_assessor import (
            FixtureAssessor,
        )

        job_analysis = JobAnalysisService(FixtureExtractor())
        assessment = OpportunityAssessmentService(FixtureAssessor())
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit(
                "OPENAI_API_KEY is not set. Pass --offline-fixtures for smoke, "
                "or set the key for live FR-002/FR-003."
            )
        try:
            import truststore

            truststore.inject_into_ssl()
        except ImportError:
            pass
        from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor
        from career_intelligence.opportunity_assessment.openai_assessor import OpenAIAssessor

        job_analysis = JobAnalysisService(OpenAIJobExtractor())
        assessment = OpportunityAssessmentService(OpenAIAssessor())

    deps = WorkflowDependencies(
        profile=profile,
        job_analysis=job_analysis,
        assessment=assessment,
        portfolio_matching=PortfolioMatchingService(DeterministicMatcher()),
        application_strategy=ApplicationStrategyService(DeterministicStrategyPlanner()),
        store=store,
        opportunities=opportunities,
    )
    injection = None
    if fail_node is not None:
        injection = FailureInjection(
            node_id=fail_node,
            fail_count=fail_count,
            kind=failure_kind,  # type: ignore[arg-type]
        )
    policy = RetryPolicy(
        max_attempts=max_attempts,
        yield_after_retry_schedule=yield_after_retry,
    )
    return ApplicationWorkflowRunner(
        deps,
        retry_policy=policy,
        failure_injection=injection,
    )


def print_summary(
    state: WorkflowState,
    checkpoint_dir: Path,
    *,
    opportunities: OpportunityService | None = None,
) -> None:
    print("=" * 72)
    print("FR-008 Workflow Manual Validation")
    print("=" * 72)
    print(f"run_id: {state.run_id}")
    print(f"status: {state.status}")
    print(f"checkpoint: {checkpoint_dir / f'{state.run_id}.json'}")
    print(f"current_node: {state.control.current_node}")
    if state.retry is not None:
        print(
            f"retry: node={state.retry.node_id} "
            f"attempts={state.retry.attempts_used}/{state.retry.max_attempts} "
            f"exhausted={state.retry.exhausted} "
            f"classification={state.retry.last_classification}"
        )
    if state.acquisition:
        print(f"source_kind: {state.acquisition.source_kind}")
        if state.acquisition.source_identifier:
            print(f"source_identifier: {state.acquisition.source_identifier}")
        print(f"title: {state.acquisition.title}")
        print(f"company: {state.acquisition.company}")
    if state.artefacts.strategy:
        print(f"pursuit_posture: {state.artefacts.strategy.pursuit_posture}")
        print(f"application_tier: {state.artefacts.strategy.application_tier}")
    if state.artefacts.opportunity_id:
        print(f"opportunity_id: {state.artefacts.opportunity_id}")
    if state.approval.pending_kind:
        print(f"pending_approval: {state.approval.pending_kind}")
        print(f"pending_options: {state.approval.pending_options}")
        print(f"pending_message: {state.approval.pending_message}")
    if state.approval.owner_decision:
        print(f"owner_decision: {state.approval.owner_decision}")
    if opportunities is not None and state.artefacts.opportunity_id:
        try:
            opp = opportunities.get(state.artefacts.opportunity_id)
            print("opportunity_summary:")
            print(f"  status: {opp.status}")
            print(f"  company: {opp.identity.company}")
            print(f"  title: {opp.identity.title}")
            print(
                f"  decision: {opp.decision.decision if opp.decision else None}"
            )
            print(f"  artifacts: {len(opp.artifact_paths)}")
        except Exception as error:  # noqa: BLE001
            print(f"  (could not load opportunity: {error})")
    print("events:")
    for event in state.execution.events:
        extra = ""
        if event.node_id:
            extra += f" node={event.node_id}"
        if event.attempt is not None:
            extra += f" attempt={event.attempt}"
        if event.recoverable is not None and event.event_type in {
            "node_failed",
            "retry_scheduled",
            "retry_exhausted",
        }:
            extra += f" recoverable={event.recoverable}"
        if event.decision:
            extra += f" decision={event.decision}"
        if event.checkpoint_reason:
            extra += f" reason={event.checkpoint_reason}"
        print(f"  - {event.event_type}{extra}")
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "show":
        store = JsonDirectoryCheckpointStore(args.checkpoint_dir)
        state = store.load(args.run_id)
        opportunities = OpportunityService.from_path(args.opportunities_dir)
        print_summary(state, args.checkpoint_dir, opportunities=opportunities)
        if args.output_json is not None:
            args.output_json.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return 0

    fail_node = getattr(args, "fail_node", None)
    fail_count = getattr(args, "fail_count", 1)
    failure_kind = getattr(args, "failure_kind", "recoverable")
    yield_after_retry = getattr(args, "yield_after_retry", False)
    max_attempts = getattr(args, "max_attempts", 3)

    runner = build_runner(
        checkpoint_dir=args.checkpoint_dir,
        opportunities_dir=args.opportunities_dir,
        profile_path=args.profile_path,
        offline_fixtures=args.offline_fixtures,
        max_attempts=max_attempts,
        fail_node=fail_node,
        fail_count=fail_count,
        failure_kind=failure_kind,
        yield_after_retry=yield_after_retry,
    )

    if args.command == "start":
        if args.source == "export":
            source = LocalFileAcquisitionAdapter(
                args.job_file,
                title=args.title,
                company=args.company,
                source_url=args.source_url,
            )
        else:
            text = args.job_file.read_text(encoding="utf-8")
            source = PasteJobInput(
                raw_text=text,
                title=args.title,
                company=args.company,
                source_url=args.source_url,
            )
        state = runner.start(source)
    elif args.command == "continue":
        state = runner.continue_run(args.run_id)
    else:
        # resume or reload — same public contract (idempotent for completed runs)
        state = runner.resume(args.run_id, args.decision)

    print_summary(state, args.checkpoint_dir, opportunities=runner.opportunities)
    if args.output_json is not None:
        args.output_json.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        print(f"Wrote {args.output_json}")

    offline = " --offline-fixtures" if getattr(args, "offline_fixtures", False) else ""
    if state.status == "awaiting_owner":
        print(
            "Interrupted for owner review. Resume with:\n"
            f"  python {SCRIPT} resume "
            f"--run-id {state.run_id} --decision apply|skip|defer{offline}"
        )
        return 0
    if (
        state.status == "running"
        and state.retry is not None
        and not state.retry.exhausted
    ):
        print(
            "Recoverable failure checkpointed; continue with:\n"
            f"  python {SCRIPT} continue --run-id {state.run_id}{offline}"
        )
        return 3
    if state.status == "running" and state.control.last_error is not None:
        print(
            "Apply side-effect paused with recoverable error; re-run resume with the "
            f"same decision.\n  last_error: {state.control.last_error}",
            file=sys.stderr,
        )
        return 2
    if state.status == "failed":
        print(f"FAILED: {state.control.last_error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
