"""Builders for M4 opportunity comparison tests."""

from __future__ import annotations

from datetime import UTC, datetime

from career_intelligence.opportunities.models import (
    Opportunity,
    OpportunityIdentity,
    OwnerDecisionRecord,
    OutcomeRecord,
    StrategySummary,
)


def make_opportunity(
    opportunity_id: str,
    *,
    company: str = "Example Co",
    title: str = "AI Engineer",
    status: str = "assessed",
    pursuit_posture: str | None = "prioritise",
    application_tier: str | None = "platinum",
    technical_fit: str = "strong",
    commercial_fit: str = "moderate",
    portfolio_fit: str = "strong",
    decision: str | None = None,
    follow_up_date: object | None = None,
    incomplete: bool = False,
) -> Opportunity:
    """Build an in-memory Opportunity with controllable ranking inputs."""
    now = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)
    identity = OpportunityIdentity(
        opportunity_id=opportunity_id,
        created_at=now,
        source_kind="manual",
        company=company,
        title=title,
    )
    summary = None
    if not incomplete:
        assert pursuit_posture is not None and application_tier is not None
        summary = StrategySummary(
            pursuit_posture=pursuit_posture,  # type: ignore[arg-type]
            application_tier=application_tier,  # type: ignore[arg-type]
            practical_value="career_priority",
            technical_fit=technical_fit,  # type: ignore[arg-type]
            commercial_fit=commercial_fit,  # type: ignore[arg-type]
            portfolio_fit=portfolio_fit,  # type: ignore[arg-type]
        )
    decision_record = None
    if decision is not None:
        decision_record = OwnerDecisionRecord(
            decision=decision,  # type: ignore[arg-type]
            decided_at=now,
        )
    outcome = None
    if follow_up_date is not None:
        outcome = OutcomeRecord(
            outcome="pending",
            follow_up_date=follow_up_date,  # type: ignore[arg-type]
            updated_at=now,
        )
    return Opportunity(
        identity=identity,
        status=status,  # type: ignore[arg-type]
        decision=decision_record,
        outcome=outcome,
        strategy_summary=summary,
        updated_at=now,
    )


# Stable Crockford ULIDs for deterministic tie-break tests
ID_A = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"
ID_B = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAB"
ID_C = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAC"
ID_D = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAD"
ID_E = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAE"
ID_F = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAF"
