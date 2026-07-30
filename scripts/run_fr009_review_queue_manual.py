#!/usr/bin/env python3
"""Manual validation runner for FR-009 M1 pre-review persistence + review queue.

Examples:
  # Full demo in a scratch workspace (no live data touched)
  python scripts/run_fr009_review_queue_manual.py demo \\
      --workspace data/_fr009_m1_manual --offline-fixtures

  # Inspect the derived queue over any opportunities directory
  python scripts/run_fr009_review_queue_manual.py queue \\
      --opportunities-dir data/opportunities
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_data_engineer,
)
from career_intelligence.opportunities import OpportunityService
from career_intelligence.orchestration import PasteJobInput
from career_intelligence.review_queue import ReviewQueue, ReviewQueueService

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPPORTUNITIES_DIR = REPO_ROOT / "data" / "opportunities"

# Reuse the FR-008 dependency wiring rather than duplicating provider selection.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_fr008_workflow_manual import build_runner  # noqa: E402

FIXTURE_JOBS = (
    posting_data_engineer,
    posting_ai_engineer,
    posting_applied_ai_engineer,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FR-009 M1 manual validation (pre-review persistence + queue)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Run fixture jobs, decide, and show the queue")
    demo.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Scratch directory for checkpoints + opportunities (created if absent)",
    )
    demo.add_argument("--profile-path", type=Path, default=None)
    demo.add_argument("--offline-fixtures", action="store_true")

    queue = sub.add_parser("queue", help="Print the derived queue for a store")
    queue.add_argument(
        "--opportunities-dir", type=Path, default=DEFAULT_OPPORTUNITIES_DIR
    )
    queue.add_argument(
        "--reference-date",
        default=None,
        help="ISO date used for defer evaluation (default: today, UTC)",
    )

    return parser


def print_queue(title: str, queue: ReviewQueue) -> None:
    print("-" * 72)
    print(f"{title} (scope={queue.scope}, reference_date={queue.reference_date})")
    print("-" * 72)
    if not queue.items:
        print("  (no eligible opportunities)")
    for item in queue.items:
        print(
            f"  {item.rank}. {item.title} @ {item.company} "
            f"[{item.pursuit_posture} / {item.application_tier} / "
            f"fit {item.fit_strength}/15] {item.opportunity_id}"
        )
        for reason in item.reasons:
            print(f"       - {reason}")
    for verdict in queue.excluded:
        reasons = ", ".join(verdict.exclusion_reasons)
        print(f"  excluded: {verdict.opportunity_id} ({reasons})")


def run_demo(args: argparse.Namespace) -> int:
    checkpoints = args.workspace / "workflow_runs"
    opportunities_dir = args.workspace / "opportunities"

    def runner():  # fresh instances per call, like separate processes
        return build_runner(
            checkpoint_dir=checkpoints,
            opportunities_dir=opportunities_dir,
            profile_path=args.profile_path,
            offline_fixtures=args.offline_fixtures,
        )

    print("=" * 72)
    print("FR-009 M1 Manual Validation")
    print("=" * 72)

    paused_runs: list[tuple[str, str]] = []
    for factory in FIXTURE_JOBS:
        posting = factory()
        state = runner().start(
            PasteJobInput(
                raw_text=posting.raw_text,
                title=posting.title,
                company=posting.company,
            )
        )
        print(
            f"started {factory.__name__}: status={state.status} "
            f"opportunity_id={state.artefacts.opportunity_id}"
        )
        if state.status != "awaiting_owner" or state.artefacts.opportunity_id is None:
            print(f"FAILED before owner review: {state.control.last_error}")
            return 1
        paused_runs.append((state.run_id, state.artefacts.opportunity_id))

    service = OpportunityService.from_path(opportunities_dir)
    queue_service = ReviewQueueService(service)
    print(
        f"\nA. Persisted before any owner decision: "
        f"{len(service.list_opportunities())} records, "
        f"decisions={[record.decision for record in service.list_opportunities()]}"
    )
    print_queue("Awaiting review", queue_service.list_awaiting_review())

    print("\nB. Recording one decision of each kind")
    decisions = ["apply", "skip", "defer"]
    ranked = queue_service.list_awaiting_review().opportunity_ids
    by_opportunity = {opportunity_id: run_id for run_id, opportunity_id in paused_runs}
    applied: tuple[str, str] | None = None
    for opportunity_id, decision in zip(ranked, decisions, strict=True):
        run_id = by_opportunity[opportunity_id]
        done = runner().resume(run_id, decision)
        record = OpportunityService.from_path(opportunities_dir).get(opportunity_id)
        print(
            f"  {decision}: run={done.run_id} status={done.status} "
            f"same_record={record.opportunity_id == opportunity_id} "
            f"stored_decision={record.decision.decision if record.decision else None} "
            f"pipeline_status={record.status}"
        )
        if decision == "apply":
            applied = (run_id, opportunity_id)

    print("\nC. Replaying a completed run (idempotency check)")
    assert applied is not None
    replay_run, replay_opportunity = applied
    replayed = runner().resume(replay_run, "apply")
    total = len(OpportunityService.from_path(opportunities_dir).list_opportunities())
    print(
        f"  replay status={replayed.status} "
        f"opportunity_id={replayed.artefacts.opportunity_id} "
        f"(expected {replay_opportunity}) total_records={total}"
    )

    print("\nD. Queue after decisions (nothing deleted)")
    fresh = ReviewQueueService(OpportunityService.from_path(opportunities_dir))
    print_queue("Awaiting review", fresh.list_awaiting_review())
    print_queue("Active", fresh.list_active_opportunities())
    print(
        f"\nStored records still on disk: "
        f"{len(OpportunityService.from_path(opportunities_dir).list_opportunities())}"
    )
    return 0


def run_queue(args: argparse.Namespace) -> int:
    from datetime import date

    reference = date.fromisoformat(args.reference_date) if args.reference_date else None
    service = ReviewQueueService(OpportunityService.from_path(args.opportunities_dir))
    print_queue(
        "Awaiting review", service.list_awaiting_review(reference_date=reference)
    )
    print_queue(
        "Active", service.list_active_opportunities(reference_date=reference)
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        return run_demo(args)
    return run_queue(args)


if __name__ == "__main__":
    raise SystemExit(main())
