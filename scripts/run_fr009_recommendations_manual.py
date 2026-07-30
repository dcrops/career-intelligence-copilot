#!/usr/bin/env python3
"""Manual validation runner for FR-009 M4 opportunity recommendations.

Examples:
  python scripts/run_fr009_recommendations_manual.py demo \\
      --workspace data/_fr009_m4_manual --offline-fixtures
  python scripts/run_fr009_recommendations_manual.py recommend \\
      --opportunities data/opportunities
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from career_intelligence.duplicates import DuplicateDetectionService
from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_data_engineer,
)
from career_intelligence.opportunities import (
    DuplicateReviewService,
    OpportunityReviewService,
    OpportunityService,
)
from career_intelligence.orchestration import PasteJobInput
from career_intelligence.recommendations import OpportunityRecommendationService
from career_intelligence.review_queue import ReviewQueueService

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_fr008_workflow_manual import build_runner  # noqa: E402

STAMP = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)
FIXTURE_JOBS = (
    posting_data_engineer,
    posting_ai_engineer,
    posting_applied_ai_engineer,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FR-009 M4 recommendations manual validation"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Acquire fixtures and print recommendations")
    demo.add_argument("--workspace", type=Path, required=True)
    demo.add_argument("--profile-path", type=Path, default=None)
    demo.add_argument("--offline-fixtures", action="store_true")
    recommend = sub.add_parser(
        "recommend", help="Read-only recommendations for an existing store"
    )
    recommend.add_argument("--opportunities", type=Path, required=True)
    recommend.add_argument(
        "--scope",
        choices=("awaiting_review", "active"),
        default="awaiting_review",
    )
    return parser


def print_report(report) -> None:
    print("-" * 72)
    print(
        f"Recommendations scope={report.scope} "
        f"included={report.included_count} excluded={report.excluded_count}"
    )
    print("-" * 72)
    if not report.items:
        print("  (empty)")
    for item in report.items:
        print(
            f"  {item.rank}. [{item.priority_band}/{item.urgency}] "
            f"{item.title} @ {item.company} ({item.opportunity_id})"
        )
        print(
            f"       next={item.recommended_next_action} "
            f"posture={item.pursuit_posture} value={item.practical_value} "
            f"fit={item.fit_strength}/15 tier={item.application_tier}"
        )
        if item.duplicate_group_size:
            print(f"       represents {item.duplicate_group_size} advertisements")
        for label, values in (
            ("+", item.positives),
            ("-", item.negatives),
            ("?", item.missing),
            ("~", item.trade_offs),
        ):
            for value in values[:3]:
                print(f"       {label} {value}")


def run_recommend(args: argparse.Namespace) -> int:
    opportunities = OpportunityService.from_path(args.opportunities)
    service = OpportunityRecommendationService(opportunities)
    if args.scope == "active":
        report = service.recommend_active(reference_date=REF, generated_at=STAMP)
    else:
        report = service.recommend_awaiting_review(
            reference_date=REF, generated_at=STAMP
        )
    print(f"records: {len(opportunities.list_opportunities())}")
    print_report(report)
    return 0


def run_demo(args: argparse.Namespace) -> int:
    opportunities_dir = args.workspace / "opportunities"
    runner = build_runner(
        checkpoint_dir=args.workspace / "workflow_runs",
        opportunities_dir=opportunities_dir,
        profile_path=args.profile_path,
        offline_fixtures=args.offline_fixtures,
    )

    print("=" * 72)
    print("FR-009 M4 Recommendations Manual Validation")
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
    recommendations = OpportunityRecommendationService(opportunities)
    review = OpportunityReviewService(opportunities)
    duplicates = DuplicateReviewService(opportunities)
    queue = ReviewQueueService(opportunities)

    print("\nA. Baseline recommendations (quality order, explained)")
    baseline = recommendations.recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    print_report(baseline)
    replayed = recommendations.recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    print(f"  stable replay: {baseline == replayed}")

    weak, *_rest = ids
    print("\nB. Pin override raises a record without changing fit values")
    before_fit = next(
        item.fit_strength for item in baseline.items if item.opportunity_id == weak
    )
    review.pin(weak, occurred_at=STAMP)
    pinned = recommendations.recommend_awaiting_review(
        reference_date=REF, generated_at=STAMP
    )
    print(f"  pinned first: {pinned.opportunity_ids[0] == weak}")
    print(
        f"  fit unchanged: "
        f"{pinned.items[0].fit_strength == before_fit} ({before_fit}/15)"
    )
    review.unpin(weak, occurred_at=STAMP)

    print("\nC. Confirm a duplicate — member leaves recommendations")
    # Acquire a second copy of the first fixture if we only have distinct fixtures.
    # For this demo, confirm the first two when detection surfaces them; otherwise skip.
    detection = DuplicateDetectionService(opportunities)
    candidates = detection.list_candidates(generated_at=STAMP).candidates
    if candidates:
        pair = candidates[0]
        duplicates.confirm_duplicate(
            pair.other_opportunity_id, pair.opportunity_id, occurred_at=STAMP
        )
        after = recommendations.recommend_awaiting_review(
            reference_date=REF, generated_at=STAMP
        )
        print(f"  member excluded: {pair.other_opportunity_id not in after.opportunity_ids}")
        canonical = next(
            (item for item in after.items if item.opportunity_id == pair.opportunity_id),
            None,
        )
        print(
            f"  canonical annotated: "
            f"{canonical.duplicate_group_size if canonical else None}"
        )
    else:
        print("  (no duplicate candidates among fixtures — skipped)")

    print("\nD. Apply decision changes next action wording")
    target = baseline.opportunity_ids[0]
    opportunities.record_decision(target, "apply")
    active = recommendations.recommend_active(reference_date=REF, generated_at=STAMP)
    item = next(entry for entry in active.items if entry.opportunity_id == target)
    print(f"  next action: {item.recommended_next_action}")
    print(
        "  no false awaiting-action wording: "
        f"{'awaiting owner action' not in ' | '.join(item.ranking_reasons).lower()}"
    )
    print(
        f"  queue awaiting excludes applied: "
        f"{target not in queue.list_awaiting_review(reference_date=REF).opportunity_ids}"
    )

    print("\nE. Read-only store integrity")
    print(f"  opportunity count unchanged: {len(opportunities.list_opportunities())}")
    print_report(active)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "recommend":
        return run_recommend(args)
    return run_demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
