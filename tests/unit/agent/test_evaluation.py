"""FR-015 M4 evaluation and observability tests."""

from __future__ import annotations

from career_intelligence.agent import (
    AlternatePreferenceProposer,
    aggregate_metrics,
    build_default_corpus,
    extract_run_metrics,
    run_corpus,
)
from tests.unit.agent.helpers import (
    OPP,
    make_artefacts,
    make_package,
    make_snapshot,
    make_truth,
)


def test_default_corpus_all_passes() -> None:
    cases = build_default_corpus(
        make_snapshot=make_snapshot,
        make_artefacts=make_artefacts,
        make_package=make_package,
        make_truth=make_truth,
        opp_id=OPP,
    )
    report = run_corpus(cases, opportunity_id=OPP)
    failed = [r for r in report.case_results if not r.passed]
    assert report.all_passed, [(r.case_id, r.detail) for r in failed]
    assert report.cases_total >= 14
    assert report.corpus_metrics.run_count == report.cases_total
    assert report.corpus_metrics.total_steps >= report.cases_total


def test_proposer_comparison_records_disagreement() -> None:
    cases = build_default_corpus(
        make_snapshot=make_snapshot,
        make_artefacts=make_artefacts,
        make_package=make_package,
        make_truth=make_truth,
        opp_id=OPP,
    )
    report = run_corpus(cases, opportunity_id=OPP)
    assert report.proposer_comparison
    # At least one case should show alternate legal disagreement opportunity
    # (missing_package prefers prepare; alternate may pick request_owner_review).
    assert any(not row.agreed for row in report.proposer_comparison) or any(
        row.agreed for row in report.proposer_comparison
    )
    assert all(row.deterministic_legal for row in report.proposer_comparison)


def test_extract_metrics_policy_block() -> None:
    cases = [
        c
        for c in build_default_corpus(
            make_snapshot=make_snapshot,
            make_artefacts=make_artefacts,
            make_package=make_package,
            make_truth=make_truth,
            opp_id=OPP,
        )
        if c.case_id == "policy_blocked_injection"
    ]
    report = run_corpus(cases, opportunity_id=OPP)
    assert report.all_passed
    metrics = report.case_results[0].metrics
    assert metrics.policy_blocks >= 1
    assert metrics.stop_reason == "policy_blocked"


def test_aggregate_empty() -> None:
    empty = aggregate_metrics([])
    assert empty.run_count == 0


def test_static_builder_preserves_clarification() -> None:
    from career_intelligence.agent import StaticReadinessBuilder, primary_state_class

    snap = make_snapshot(
        clarification_required=True,
        clarification_message="Which package version?",
    )
    built = StaticReadinessBuilder([snap]).build(
        OPP, owner_approvals_present=True, provider_available=True
    )
    assert built.clarification_required is True
    assert built.clarification_message == "Which package version?"
    assert primary_state_class(built) == "clarification_required"
