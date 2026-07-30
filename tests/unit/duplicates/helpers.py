"""Builders for FR-009 M3 duplicate-detection tests.

Identity facets are fully controllable because detection is an identity-evidence
problem: tests must be able to express "same platform id, different company" and
"identical description text, nothing else".
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunities.models import (
    DuplicateRejection,
    DuplicateRelation,
    Opportunity,
    OpportunityIdentity,
    StrategySummary,
)
from career_intelligence.opportunities.yaml_store import YamlDirectoryOpportunityStore

STAMP = datetime(2026, 7, 30, 9, 0, 0, tzinfo=UTC)
CREATED = datetime(2026, 7, 20, 8, 0, 0, tzinfo=UTC)

ID_1 = "opp_01ARZ3NDEKTSV4RRFFQ69G5F01"
ID_2 = "opp_01ARZ3NDEKTSV4RRFFQ69G5F02"
ID_3 = "opp_01ARZ3NDEKTSV4RRFFQ69G5F03"
ID_4 = "opp_01ARZ3NDEKTSV4RRFFQ69G5F04"

FINGERPRINT = "a" * 64
OTHER_FINGERPRINT = "b" * 64


def ad(
    opportunity_id: str,
    *,
    source_kind: str = "manual",
    platform_job_id: str | None = None,
    canonical_url: str | None = None,
    source_url: str | None = None,
    company: str | None = "Acme Pty Ltd",
    title: str | None = "AI Engineer",
    location_text: str | None = "Sydney, NSW",
    content_fingerprint: str | None = None,
    created_at: datetime | None = None,
    with_artifacts: bool = False,
    duplicate_of: str | None = None,
    rejected_against: tuple[str, ...] = (),
) -> Opportunity:
    """One discovered advertisement with explicit identity evidence."""
    identity = OpportunityIdentity(
        opportunity_id=opportunity_id,
        created_at=created_at or CREATED,
        source_kind=source_kind,  # type: ignore[arg-type]
        platform_job_id=platform_job_id,
        canonical_url=canonical_url,  # type: ignore[arg-type]
        source_url=source_url,  # type: ignore[arg-type]
        company=company,
        title=title,
        location_text=location_text,
        content_fingerprint=content_fingerprint,
    )
    record = Opportunity(
        identity=identity,
        status="assessed",
        decision=None,
        strategy_summary=StrategySummary(
            pursuit_posture="prioritise",
            application_tier="platinum",
            practical_value="career_priority",
            technical_fit="strong",
            commercial_fit="moderate",
            portfolio_fit="strong",
        ),
        artifact_paths=(
            {name: f"artifacts/{opportunity_id}/{name}" for name in ("posting.json",)}
            if with_artifacts
            else {}
        ),
        duplicate=(
            DuplicateRelation(
                duplicate_of=duplicate_of,
                confirmed_at=STAMP,
                evidence=("owner_judgment",),
            )
            if duplicate_of is not None
            else None
        ),
        duplicate_rejections=tuple(
            DuplicateRejection(other_opportunity_id=other, rejected_at=STAMP)
            for other in rejected_against
        ),
        updated_at=STAMP,
    )
    return record


def store_with(tmp_path: Path, records: list[Opportunity]) -> OpportunityService:
    """A real YAML store so persistence and reload behaviour is exercised."""
    store = YamlDirectoryOpportunityStore(tmp_path / "opportunities")
    for record in records:
        # create_index_only refuses artefact claims; restore them with a save so
        # canonical-recommendation inputs survive the round-trip.
        store.create_index_only(record.model_copy(update={"artifact_paths": {}}))
        if record.artifact_paths:
            store.save(record)
    return OpportunityService(store=store)
