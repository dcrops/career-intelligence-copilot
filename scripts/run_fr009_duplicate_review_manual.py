#!/usr/bin/env python3
"""Manual validation runner for FR-009 M3 duplicate review.

Acquires the same fixture vacancy twice (the cross-source situation this milestone
exists for) plus one unrelated vacancy, then walks the owner through detection,
confirmation, rejection and canonical selection.

Examples:
  python scripts/run_fr009_duplicate_review_manual.py demo \\
      --workspace data/_fr009_m3_manual --offline-fixtures
  python scripts/run_fr009_duplicate_review_manual.py candidates \\
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
    posting_data_engineer,
)
from career_intelligence.opportunities import (
    DuplicateReviewService,
    OpportunityService,
)
from career_intelligence.orchestration import PasteJobInput
from career_intelligence.review_queue import ReviewQueueService

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_fr008_workflow_manual import build_runner  # noqa: E402

STAMP = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
REF = date(2026, 7, 30)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FR-009 M3 duplicate review manual validation"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Acquire duplicates and exercise owner actions")
    demo.add_argument("--workspace", type=Path, required=True)
    demo.add_argument("--profile-path", type=Path, default=None)
    demo.add_argument("--offline-fixtures", action="store_true")
    candidates = sub.add_parser(
        "candidates", help="Read-only candidate report for an existing store"
    )
    candidates.add_argument("--opportunities", type=Path, required=True)
    return parser


def print_candidates(report) -> None:
    print("-" * 72)
    print(f"Duplicate candidates ({len(report.candidates)}) as at {report.generated_at}")
    print("-" * 72)
    if not report.candidates:
        print("  (none unresolved)")
    for candidate in report.candidates:
        print(f"  [{candidate.confidence}] {candidate.opportunity_id} ~ {candidate.other_opportunity_id}")
        print(f"       {candidate.rationale}")
        print(f"       matching:  {', '.join(candidate.comparison.matching) or '-'}")
        print(f"       differing: {', '.join(candidate.comparison.differing) or '-'}")
        print(f"       unknown:   {', '.join(candidate.comparison.unknown) or '-'}")


def print_groups(detection: DuplicateDetectionService) -> None:
    groups = detection.list_groups()
    print(f"  confirmed groups: {len(groups)}")
    for group in groups:
        print(
            f"    canonical={group.canonical_opportunity_id} "
            f"members={list(group.member_opportunity_ids)} size={group.size}"
        )


def run_candidates(args: argparse.Namespace) -> int:
    opportunities = OpportunityService.from_path(args.opportunities)
    detection = DuplicateDetectionService(opportunities)
    print(f"records: {len(opportunities.list_opportunities())}")
    print_candidates(detection.list_candidates())
    print_groups(detection)
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
    print("FR-009 M3 Duplicate Review Manual Validation")
    print("=" * 72)

    # The same vacancy acquired twice, then an unrelated vacancy.
    acquisitions = (
        ("ai_engineer (first source)", posting_ai_engineer),
        ("ai_engineer (second source)", posting_ai_engineer),
        ("data_engineer (unrelated)", posting_data_engineer),
    )
    ids: list[str] = []
    for label, factory in acquisitions:
        posting = factory()
        state = runner.start(
            PasteJobInput(
                raw_text=posting.raw_text,
                title=posting.title,
                company=posting.company,
            )
        )
        if state.status != "awaiting_owner" or state.artefacts.opportunity_id is None:
            print(f"FAILED: {label}: {state.control.last_error}")
            return 1
        ids.append(state.artefacts.opportunity_id)
        print(f"persisted {label}: {state.artefacts.opportunity_id}")

    first, second, unrelated = ids
    opportunities = OpportunityService.from_path(opportunities_dir)
    detection = DuplicateDetectionService(opportunities)
    duplicates = DuplicateReviewService(opportunities)
    queue = ReviewQueueService(opportunities)

    print("\nA. Detection surfaces the pair with evidence")
    report = detection.list_candidates(generated_at=STAMP)
    print_candidates(report)
    pair_found = any(
        set(candidate.pair) == {first, second} for candidate in report.candidates
    )
    print(f"  same-vacancy pair suggested: {pair_found}")
    print(f"  unrelated vacancy involved: {any(unrelated in c.pair for c in report.candidates)}")

    print("\nB. Unresolved candidates repeat identically and hide nothing")
    repeat = detection.list_candidates(generated_at=STAMP)
    print(f"  stable across scans: {repeat.candidates == report.candidates}")
    awaiting = queue.list_awaiting_review(reference_date=REF).opportunity_ids
    print(f"  both still awaiting decision: {first in awaiting and second in awaiting}")

    print("\nC. Canonical recommendation before confirmation (advisory)")
    duplicates.confirm_duplicate(second, first, evidence=("identity_facets",), occurred_at=STAMP)
    recommendation = detection.recommend_canonical(second)
    print(f"  current canonical:     {recommendation.current_canonical_opportunity_id}")
    print(f"  recommended canonical: {recommendation.recommended_opportunity_id}")
    print(f"  owner confirmation required: {recommendation.owner_confirmation_required}")
    for reason in recommendation.reasons:
        print(f"       - {reason}")

    print("\nD. Confirmation links records without deleting them")
    print(f"  records preserved: {len(opportunities.list_opportunities())} (expected 3)")
    print_groups(detection)
    projection = queue.list_awaiting_review(reference_date=REF)
    print(f"  duplicate hidden from queue: {second not in projection.opportunity_ids}")
    print(f"  canonical still in queue:    {first in projection.opportunity_ids}")
    print(f"  pair no longer suggested:    {detection.candidates_for(second) == ()}")
    member = opportunities.get(second)
    print(f"  artefact snapshots intact:   {len(member.artifact_paths)} files")
    print(f"  decision untouched:          {member.decision is None}")

    print("\nE. Owner confirms a different canonical")
    duplicates.confirm_canonical(second, occurred_at=STAMP)
    print_groups(detection)
    print(f"  records preserved: {len(opportunities.list_opportunities())} (expected 3)")
    print(f"  new canonical has no relation: {opportunities.get(second).duplicate is None}")
    print(
        "  previous canonical now a member: "
        f"{opportunities.get(first).duplicate.duplicate_of == second}"
    )

    print("\nF. Rejection stops a suggestion returning")
    duplicates.reject_duplicate(second, unrelated, note="different role family", occurred_at=STAMP)
    after_reject = detection.list_candidates(generated_at=STAMP)
    print(f"  rejected pair suggested again: {any(set(c.pair) == {second, unrelated} for c in after_reject.candidates)}")
    print(f"  unrelated record still present: {opportunities.get(unrelated) is not None}")

    print("\nG. Idempotency and audit")
    before = opportunities.get(second)
    duplicates.confirm_canonical(second, occurred_at=STAMP)
    duplicates.reject_duplicate(unrelated, second, occurred_at=STAMP)
    after = opportunities.get(second)
    print(f"  repeat actions changed nothing: {after == before}")
    print(f"  audit trail: {[entry.action for entry in after.review_actions]}")
    print(f"  rejections recorded once: {len(after.duplicate_rejections)}")
    print_candidates(detection.list_candidates(generated_at=STAMP))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "candidates":
        return run_candidates(args)
    return run_demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
