"""Unit tests for opportunity domain models (M1)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_intelligence.opportunities.models import (
    Opportunity,
    OpportunityIdentity,
    StrategySummary,
)
from career_intelligence.opportunities.ulid import generate_ulid


def _identity(**overrides: object) -> OpportunityIdentity:
    payload = {
        "opportunity_id": f"opp_{generate_ulid()}",
        "created_at": datetime.now(UTC),
        "source_kind": "manual",
        "company": "Example",
        "title": "AI Engineer",
    }
    payload.update(overrides)
    return OpportunityIdentity.model_validate(payload)


def _summary(**overrides: object) -> StrategySummary:
    payload = {
        "pursuit_posture": "prioritise",
        "application_tier": "platinum",
        "practical_value": "career_priority",
        "technical_fit": "strong",
        "commercial_fit": "moderate",
        "portfolio_fit": "strong",
    }
    payload.update(overrides)
    return StrategySummary.model_validate(payload)


def test_opportunity_id_shape_accepts_opp_ulid() -> None:
    identity = _identity()
    assert identity.opportunity_id.startswith("opp_")
    assert len(identity.opportunity_id) == 4 + 26


def test_opportunity_id_rejects_invalid_shape() -> None:
    with pytest.raises(ValidationError):
        _identity(opportunity_id="opp_not-a-ulid")


def test_default_status_is_assessed() -> None:
    now = datetime.now(UTC)
    opportunity = Opportunity(
        identity=_identity(),
        strategy_summary=_summary(),
        updated_at=now,
    )
    assert opportunity.status == "assessed"
    assert opportunity.decision is None
    assert opportunity.outcome is None


def test_round_trip_serialisation() -> None:
    now = datetime.now(UTC)
    opportunity = Opportunity(
        identity=_identity(source_kind="seek", platform_job_id="123"),
        strategy_summary=_summary(),
        artifact_paths={"posting.json": "artifacts/opp_x/posting.json"},
        updated_at=now,
    )
    restored = Opportunity.model_validate(opportunity.model_dump(mode="json"))
    assert restored == opportunity


def test_unknown_artifact_key_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown artifact keys"):
        Opportunity(
            identity=_identity(),
            strategy_summary=_summary(),
            artifact_paths={"extra.json": "artifacts/x/extra.json"},
            updated_at=datetime.now(UTC),
        )
