"""Deterministic canonical Opportunity recommendation (FR-009 M3).

Advisory only. The owner confirms a canonical record through
``DuplicateReviewService.confirm_canonical``; nothing here re-points a group.
"""

from __future__ import annotations

from career_intelligence.opportunities.models import Opportunity

from .models import CanonicalRecommendation

_PLATFORM_RANK: dict[str, int] = {
    # Structured platforms carry a stable listing id and canonical URL, which is what
    # later automation and re-checks need. Recruiter reposts rank last because the
    # advertiser is an intermediary rather than the employer.
    "seek": 0,
    "linkedin": 1,
    "indeed": 2,
    "other": 3,
    "manual": 4,
    "import": 5,
    "recruiter": 6,
}

_COMPLETENESS_FACETS = (
    "platform_job_id",
    "canonical_url",
    "source_url",
    "company",
    "title",
    "location_text",
    "content_fingerprint",
)


def metadata_completeness(record: Opportunity) -> int:
    """Count of populated identity facets (higher is a better canonical)."""
    identity = record.identity
    return sum(
        1 for facet in _COMPLETENESS_FACETS if getattr(identity, facet, None) is not None
    )


def recommend_canonical(records: list[Opportunity]) -> CanonicalRecommendation:
    """Recommend which advertisement should represent the group.

    Criteria, applied in order and fully deterministic:

    1. Has FR-002–FR-005 artefact snapshots (a canonical record without evidence
       cannot drive tailoring later).
    2. Advertiser is not a recruiter intermediary.
    3. Platform rank (structured listing id / canonical URL available).
    4. Identity metadata completeness.
    5. Earliest discovery (``identity.created_at``).
    6. ``opportunity_id`` ascending, so ties never depend on scan order.
    """
    if not records:
        raise ValueError("recommend_canonical requires at least one Opportunity")

    ordered = sorted(records, key=_canonical_sort_key)
    winner = ordered[0]
    current = _current_canonical_id(records)
    return CanonicalRecommendation(
        group_opportunity_ids=tuple(
            sorted(record.opportunity_id for record in records)
        ),
        recommended_opportunity_id=winner.opportunity_id,
        current_canonical_opportunity_id=current,
        reasons=_reasons(winner),
    )


def _canonical_sort_key(record: Opportunity) -> tuple[int, int, int, int, str, str]:
    identity = record.identity
    return (
        0 if record.artifact_paths else 1,
        1 if identity.source_kind == "recruiter" else 0,
        _PLATFORM_RANK.get(identity.source_kind, len(_PLATFORM_RANK)),
        -metadata_completeness(record),
        identity.created_at.isoformat(),
        record.opportunity_id,
    )


def _current_canonical_id(records: list[Opportunity]) -> str:
    for record in records:
        if record.duplicate is not None:
            return record.duplicate.duplicate_of
    return min(record.opportunity_id for record in records)


def _reasons(winner: Opportunity) -> tuple[str, ...]:
    identity = winner.identity
    reasons: list[str] = []
    if winner.artifact_paths:
        reasons.append("Has full analysis and strategy artefact snapshots")
    if identity.source_kind == "recruiter":
        reasons.append("Only recruiter-sourced advertisements available")
    else:
        reasons.append(f"Sourced from {identity.source_kind}, not a recruiter repost")
    if identity.platform_job_id is not None:
        reasons.append("Carries a platform job id for future re-checks")
    if identity.canonical_url is not None:
        reasons.append("Carries a canonical advertisement URL")
    reasons.append(f"Identity metadata completeness {metadata_completeness(winner)}/7")
    reasons.append(f"Discovered {identity.created_at.date().isoformat()}")
    return tuple(reasons)
