"""Unit tests for the FR-009 M1 queue eligibility policy."""

from __future__ import annotations

from datetime import date

from career_intelligence.opportunities.models import OpportunityReview
from career_intelligence.review_queue import evaluate_eligibility
from tests.unit.opportunity_comparison.helpers import ID_A, ID_B
from tests.unit.review_queue.helpers import REFERENCE_DATE, STAMP, queue_opportunity


def test_undecided_record_is_awaiting_review() -> None:
    verdict = evaluate_eligibility(
        queue_opportunity(ID_A),
        reference_date=REFERENCE_DATE,
        scope="awaiting_review",
    )
    assert verdict.eligible
    assert verdict.exclusion_reasons == ()


def test_applied_record_is_active_but_not_awaiting_review() -> None:
    applied = queue_opportunity(ID_A, decision="apply")
    assert evaluate_eligibility(applied, reference_date=REFERENCE_DATE).eligible
    awaiting = evaluate_eligibility(
        applied, reference_date=REFERENCE_DATE, scope="awaiting_review"
    )
    assert not awaiting.eligible
    assert awaiting.exclusion_reasons == ("decided",)


def test_skipped_record_leaves_both_scopes_but_is_still_stored() -> None:
    skipped = queue_opportunity(ID_A, decision="skip")
    for scope in ("active", "awaiting_review"):
        verdict = evaluate_eligibility(
            skipped, reference_date=REFERENCE_DATE, scope=scope  # type: ignore[arg-type]
        )
        assert not verdict.eligible
        assert verdict.exclusion_reasons == ("skipped",)


def test_undated_defer_is_treated_as_manually_deferred() -> None:
    verdict = evaluate_eligibility(
        queue_opportunity(ID_A, decision="defer"), reference_date=REFERENCE_DATE
    )
    assert verdict.exclusion_reasons == ("deferred",)


def test_defer_until_is_evaluated_against_the_explicit_reference_date() -> None:
    deferred = queue_opportunity(
        ID_A,
        decision="defer",
        review=OpportunityReview(defer_until=date(2026, 8, 15)),
    )
    assert not evaluate_eligibility(deferred, reference_date=date(2026, 8, 14)).eligible
    # On and after defer_until the record returns to the queue.
    assert evaluate_eligibility(deferred, reference_date=date(2026, 8, 15)).eligible
    assert evaluate_eligibility(deferred, reference_date=date(2026, 9, 1)).eligible


def test_archived_and_duplicate_records_are_excluded() -> None:
    archived = evaluate_eligibility(
        queue_opportunity(ID_A, review=OpportunityReview(archived_at=STAMP)),
        reference_date=REFERENCE_DATE,
    )
    assert archived.exclusion_reasons == ("archived",)

    duplicate = evaluate_eligibility(
        queue_opportunity(ID_B, duplicate_of=ID_A), reference_date=REFERENCE_DATE
    )
    assert duplicate.exclusion_reasons == ("confirmed_duplicate",)


def test_terminal_pipeline_status_is_excluded_as_closed() -> None:
    verdict = evaluate_eligibility(
        queue_opportunity(ID_A, decision="apply", status="rejected"),
        reference_date=REFERENCE_DATE,
    )
    assert verdict.exclusion_reasons == ("closed",)


def test_multiple_reasons_are_reported_in_a_stable_order() -> None:
    worst = queue_opportunity(
        ID_B,
        decision="skip",
        status="withdrawn",
        review=OpportunityReview(archived_at=STAMP),
        duplicate_of=ID_A,
    )
    first = evaluate_eligibility(worst, reference_date=REFERENCE_DATE)
    second = evaluate_eligibility(worst, reference_date=REFERENCE_DATE)
    assert first.exclusion_reasons == (
        "archived",
        "confirmed_duplicate",
        "skipped",
        "closed",
    )
    assert first == second


def test_policy_does_not_mutate_the_record() -> None:
    record = queue_opportunity(ID_A)
    before = record.model_dump(mode="json")
    evaluate_eligibility(record, reference_date=REFERENCE_DATE)
    assert record.model_dump(mode="json") == before
