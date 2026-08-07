"""Definite-identity idempotency helpers for FR-018 discovery (reuse FR-009)."""

from __future__ import annotations

from datetime import UTC, datetime
from collections.abc import Sequence

from career_intelligence.duplicates.detection import classify_pair
from career_intelligence.duplicates.evidence import compare_identities
from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.opportunities.identity import build_identity, derive_source_facets
from career_intelligence.opportunities.models import Opportunity, OpportunityIdentity

# Sentinel id for probe identities — never persisted; compare uses facets only.
_PROBE_ID = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAZ"


def identity_probe_from_url(url: str) -> OpportunityIdentity | None:
    """Build a probe identity from URL facets alone.

    Returns None when the URL cannot form definite-match facets (no platform id /
    canonical URL) — caller must not skip on URL-only evidence in that case.
    """
    platform, platform_job_id, canonical = derive_source_facets(url)
    if platform_job_id is None and canonical is None:
        return None
    return OpportunityIdentity.model_validate(
        {
            "opportunity_id": _PROBE_ID,
            "created_at": datetime.now(UTC),
            "source_kind": platform,
            "platform_job_id": platform_job_id,
            "canonical_url": canonical,
            "source_url": url,
            "company": None,
            "title": None,
            "location_text": None,
            "content_fingerprint": None,
        }
    )


def identity_probe_from_posting(posting: JobPosting) -> OpportunityIdentity:
    """Probe identity from acquired posting (includes fingerprint; not used for skip alone)."""
    return build_identity(posting, opportunity_id=_PROBE_ID, include_fingerprint=True)


def find_definite_match(
    probe: OpportunityIdentity,
    opportunities: Sequence[Opportunity],
) -> Opportunity | None:
    """Return the first Opportunity with FR-009 definite identity match to probe.

    Fingerprint-only similarity is never definite (FR-009) and will not skip.
    """
    for opportunity in opportunities:
        comparison = compare_identities(probe, opportunity.identity)
        confidence, _rationale = classify_pair(comparison)
        if confidence == "definite":
            return opportunity
    return None
