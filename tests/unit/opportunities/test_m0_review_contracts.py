"""Contract tests for the FR-009 M0 review/duplicate domain boundary (ADR-004).

These tests lock the contracts only. Queue projection, ordering extensions, pin /
defer / archive behaviour, and duplicate detection are later FR-009 milestones.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from career_intelligence.opportunities import (
    DuplicateRelation,
    Opportunity,
    OpportunityReview,
    OpportunityService,
)
from career_intelligence.opportunities.models import (
    OpportunityIdentity,
    StrategySummary,
)
from career_intelligence.opportunities.yaml_store import YamlDirectoryOpportunityStore
from career_intelligence.opportunity_comparison.ranking import rank_open_opportunities

from .helpers import create_opportunity, trusted_pipeline

LEGACY_APPLY_ONLY_ROW = {
    "identity": {
        "opportunity_id": "opp_01KY8RFAH81M9V30ZVH9TM09T5",
        "created_at": "2026-07-24T00:30:15.080566Z",
        "source_kind": "manual",
        "platform_job_id": None,
        "canonical_url": None,
        "source_url": None,
        "company": None,
        "title": None,
        "location_text": "Melbourne, VIC",
        "content_fingerprint": "6b775f2370fd6d54ee46c873059da4856b0c56bbff6af44f172497a9ad81781b",
    },
    "status": "interviewing",
    "decision": {
        "decision": "apply",
        "decided_at": "2026-07-24T00:48:16.863781Z",
        "notes": "Owner validation test",
    },
    "outcome": {
        "outcome": "pending",
        "interview_stage": "recruiter",
        "follow_up_date": None,
        "notes": "Recruiter screening scheduled",
        "updated_at": "2026-07-24T00:50:25.667178Z",
    },
    "strategy_summary": {
        "pursuit_posture": "consider",
        "application_tier": "silver",
        "practical_value": "acceptable_opportunity",
        "technical_fit": "mixed",
        "commercial_fit": "mixed",
        "portfolio_fit": "strong",
    },
    "artifact_paths": {},
    "legacy_import": None,
    "updated_at": "2026-07-24T00:50:25.667178Z",
}


def _opportunity(
    opportunity_id: str,
    *,
    pursuit_posture: str = "prioritise",
    application_tier: str = "platinum",
    technical_fit: str = "strong",
    **overrides: object,
) -> Opportunity:
    payload: dict[str, object] = {
        "identity": OpportunityIdentity(
            opportunity_id=opportunity_id,
            created_at=datetime.now(UTC),
            source_kind="manual",
            company="Example AI Co",
            title="AI Engineer",
        ),
        "strategy_summary": StrategySummary(
            pursuit_posture=pursuit_posture,
            application_tier=application_tier,
            practical_value="career_priority",
            technical_fit=technical_fit,
            commercial_fit="moderate",
            portfolio_fit="strong",
        ),
        "updated_at": datetime.now(UTC),
    }
    payload.update(overrides)
    return Opportunity(**payload)


def test_opportunity_is_durable_before_any_owner_decision(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)

    assert opportunity.decision is None
    assert opportunity.status == "assessed"

    reloaded = OpportunityService.from_path(tmp_path).get(opportunity.opportunity_id)
    assert reloaded.decision is None
    assert reloaded.strategy_summary is not None
    assert service.list_opportunities()[0].opportunity_id == opportunity.opportunity_id


def test_new_records_receive_deterministic_review_defaults(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(tmp_path)

    assert opportunity.review == OpportunityReview()
    assert opportunity.review.reviewed_at is None
    assert opportunity.review.pinned is False
    assert opportunity.review.defer_until is None
    assert opportunity.review.archived_at is None
    assert opportunity.duplicate is None


def test_apply_only_record_without_review_keys_still_loads(tmp_path: Path) -> None:
    index = {"schema_version": "1", "opportunities": [LEGACY_APPLY_ONLY_ROW]}
    (tmp_path / "index.yaml").write_text(
        yaml.safe_dump(index, sort_keys=False), encoding="utf-8"
    )

    loaded = OpportunityService.from_path(tmp_path).get(
        "opp_01KY8RFAH81M9V30ZVH9TM09T5"
    )

    assert loaded.decision is not None
    assert loaded.decision.decision == "apply"
    assert loaded.status == "interviewing"
    assert loaded.review == OpportunityReview()
    assert loaded.duplicate is None


def test_review_and_duplicate_survive_a_store_round_trip(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(tmp_path)
    store = YamlDirectoryOpportunityStore(tmp_path)
    canonical_id = "opp_01KY8RFAH81M9V30ZVH9TM09T5"

    store.save(
        opportunity.model_copy(
            update={
                "review": OpportunityReview(
                    reviewed_at=datetime(2026, 7, 29, 6, 0, tzinfo=UTC),
                    defer_until=date(2026, 8, 15),
                ),
                "duplicate": DuplicateRelation(
                    duplicate_of=canonical_id,
                    confirmed_at=datetime(2026, 7, 29, 6, 5, tzinfo=UTC),
                    evidence=("canonical_url", "owner_judgment"),
                ),
            },
            deep=True,
        )
    )

    reloaded = store.get(opportunity.opportunity_id)
    assert reloaded.review.reviewed_at == datetime(2026, 7, 29, 6, 0, tzinfo=UTC)
    assert reloaded.review.defer_until == date(2026, 8, 15)
    assert reloaded.duplicate is not None
    assert reloaded.duplicate.duplicate_of == canonical_id
    assert reloaded.duplicate.evidence == ("canonical_url", "owner_judgment")


def test_duplicate_relation_cannot_reference_itself() -> None:
    opportunity_id = "opp_01KY8WWW3AK8KKXAKM5KRZ03VE"
    with pytest.raises(ValidationError, match="different opportunity_id"):
        _opportunity(
            opportunity_id,
            duplicate=DuplicateRelation(
                duplicate_of=opportunity_id,
                confirmed_at=datetime.now(UTC),
            ),
        )


def test_archived_record_cannot_stay_pinned() -> None:
    with pytest.raises(ValidationError, match="pin must be cleared"):
        OpportunityReview(pinned=True, archived_at=datetime.now(UTC))


def test_review_update_does_not_touch_decision_or_ranking_inputs() -> None:
    original = _opportunity("opp_01KY8WWW3AK8KKXAKM5KRZ03VE")

    updated = original.model_copy(
        update={"review": OpportunityReview(pinned=True)}, deep=True
    )

    assert updated.review.pinned is True
    assert updated.identity == original.identity
    assert updated.strategy_summary == original.strategy_summary
    assert updated.artifact_paths == original.artifact_paths
    assert updated.decision == original.decision
    assert updated.status == original.status


def test_review_metadata_does_not_change_m4_ranking() -> None:
    strong = _opportunity("opp_01KY8WWW3AK8KKXAKM5KRZ03VE")
    weak = _opportunity(
        "opp_01KY8RFAH81M9V30ZVH9TM09T5",
        pursuit_posture="consider",
        application_tier="silver",
        technical_fit="mixed",
    )
    baseline = rank_open_opportunities([strong, weak])

    pinned_weak = weak.model_copy(
        update={"review": OpportunityReview(pinned=True)}, deep=True
    )
    with_review = rank_open_opportunities([strong, pinned_weak])

    assert [item.opportunity_id for item in baseline] == [
        item.opportunity_id for item in with_review
    ]
    assert [item.rank for item in baseline] == [item.rank for item in with_review]
    assert [item.reasons for item in baseline] == [
        item.reasons for item in with_review
    ]


def test_identical_content_fingerprints_stay_independent_records(
    tmp_path: Path,
) -> None:
    service = OpportunityService.from_path(tmp_path)
    created = []
    for _ in range(2):
        posting, analysis, assessment, match, strategy = trusted_pipeline()
        created.append(
            service.create_from_strategy(
                posting=posting,
                job_analysis=analysis,
                assessment=assessment,
                portfolio_match=match,
                strategy=strategy,
            )
        )

    first, second = created
    assert first.opportunity_id != second.opportunity_id
    assert (
        first.identity.content_fingerprint == second.identity.content_fingerprint
    )
    assert first.duplicate is None
    assert second.duplicate is None
