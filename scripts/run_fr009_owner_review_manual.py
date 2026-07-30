#!/usr/bin/env python3
"""Manual validation runner for FR-009 M2 owner review actions.

Examples:
  python scripts/run_fr009_owner_review_manual.py demo \\
      --workspace data/_fr009_m2_manual --offline-fixtures
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_data_engineer,
)
from career_intelligence.opportunities import (
    OpportunityReviewService,
    OpportunityService,
)
from career_intelligence.orchestration import PasteJobInput
from career_intelligence.review_queue import ReviewQueueService

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_fr008_workflow_manual import build_runner  # noqa: E402

FIXTURE_JOBS = (
    posting_data_engineer,
    posting_ai_engineer,
    posting_applied_ai_engineer,
)
STAMP = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)
FUTURE = date(2026, 8, 15)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FR-009 M2 owner review manual validation")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Persist fixtures and exercise owner review actions")
    demo.add_argument("--workspace", type=Path, required=True)
    demo.add_argument("--profile-path", type=Path, default=None)
    demo.add_argument("--offline-fixtures", action="store_true")
    return parser


def print_queue(title: str, queue) -> None:
    print("-" * 72)
    print(f"{title} (scope={queue.scope})")
    print("-" * 72)
    if not queue.items:
        print("  (empty)")
    for item in queue.items:
        print(
            f"  {item.rank}. {item.title} @ {item.company} "
            f"[{item.pursuit_posture}/{item.application_tier}] {item.opportunity_id}"
        )
        for reason in item.reasons[:3]:
            print(f"       - {reason}")


def run_demo(args: argparse.Namespace) -> int:
    checkpoints = args.workspace / "workflow_runs"
    opportunities_dir = args.workspace / "opportunities"
    runner = build_runner(
        checkpoint_dir=checkpoints,
        opportunities_dir=opportunities_dir,
        profile_path=args.profile_path,
        offline_fixtures=args.offline_fixtures,
    )

    print("=" * 72)
    print("FR-009 M2 Owner Review Manual Validation")
    print("=" * 72)

    ids: list[str] = []
    for factory in FIXTURE_JOBS:
        posting = factory()
        state = runner.start(
            PasteJobInput(
                raw_text=posting.raw_text,
                title=posting.title,
                company=posting.company,
            )
        )
        if state.status != "awaiting_owner" or state.artefacts.opportunity_id is None:
            print(f"FAILED: {factory.__name__}: {state.control.last_error}")
            return 1
        ids.append(state.artefacts.opportunity_id)
        print(f"persisted {factory.__name__}: {state.artefacts.opportunity_id}")

    opportunities = OpportunityService.from_path(opportunities_dir)
    review = OpportunityReviewService(opportunities)
    queue = ReviewQueueService(opportunities)

    weak, strong, other = ids[0], ids[1], ids[2]
    print("\nA. Mark reviewed (should stay awaiting)")
    review.mark_reviewed(strong, reviewed_at=STAMP, occurred_at=STAMP)
    awaiting = queue.list_awaiting_review(reference_date=REF)
    print(f"  reviewed stays in awaiting: {strong in awaiting.opportunity_ids}")
    print(f"  decision still None: {opportunities.get(strong).decision is None}")

    print("\nB. Pin weak-fit first, then unpin")
    before = queue.list_awaiting_review(reference_date=REF).opportunity_ids
    review.pin(weak, occurred_at=STAMP)
    pinned = queue.list_awaiting_review(reference_date=REF)
    print(f"  before[0]={before[0]}")
    print(f"  after pin[0]={pinned.opportunity_ids[0]} (expected {weak})")
    print(f"  pin reason={pinned.items[0].reasons[0]}")
    review.unpin(weak, occurred_at=STAMP)
    restored = queue.list_awaiting_review(reference_date=REF).opportunity_ids
    print(f"  after unpin[0]={restored[0]} (expected {before[0]})")

    print("\nC. Timed defer / clear defer")
    review.defer_until(other, FUTURE, reference_date=REF, occurred_at=STAMP)
    hidden = queue.list_awaiting_review(reference_date=REF)
    print(f"  hidden while deferred: {other not in hidden.opportunity_ids}")
    returned = queue.list_active_opportunities(reference_date=FUTURE)
    print(f"  active on expiry date: {other in returned.opportunity_ids}")
    review.clear_defer(other, occurred_at=STAMP)
    print(
        f"  after clear_defer awaiting: "
        f"{other in queue.list_awaiting_review(reference_date=REF).opportunity_ids}"
    )

    print("\nD. Archive / reopen")
    review.archive(other, archived_at=STAMP, occurred_at=STAMP)
    print(
        f"  archived excluded: "
        f"{other not in queue.list_active_opportunities(reference_date=REF).opportunity_ids}"
    )
    review.reopen(other, occurred_at=STAMP)
    print(
        f"  reopened awaiting: "
        f"{other in queue.list_awaiting_review(reference_date=REF).opportunity_ids}"
    )

    print("\nE. Idempotency + aggregate integrity")
    first = opportunities.get(strong)
    review.mark_reviewed(strong, reviewed_at=STAMP, occurred_at=STAMP)
    review.pin(strong, occurred_at=STAMP)
    review.pin(strong, occurred_at=STAMP)
    again = opportunities.get(strong)
    print(f"  reviewed_at preserved: {again.review.reviewed_at == first.review.reviewed_at}")
    print(f"  single opportunity count: {len(opportunities.list_opportunities())}")
    print(f"  status still assessed: {again.status == 'assessed'}")
    print(f"  actions: {[a.action for a in again.review_actions]}")

    print_queue("Awaiting review (final)", queue.list_awaiting_review(reference_date=REF))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
