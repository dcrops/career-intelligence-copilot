"""Deterministic duplicate candidate detection (FR-009 M3).

Candidates are suggestions for owner review, never merges. A false merge would hide
a real vacancy permanently, whereas a duplicate suggestion costs one owner glance —
so the rules below require corroborating evidence and treat missing data as unknown.

No single field decides a candidate. In particular a shared ``content_fingerprint``
alone is only ``possible``: the live store already contains fingerprint collision
groups produced by re-running the same posting through the workflow.
"""

from __future__ import annotations

from career_intelligence.opportunities.models import Opportunity

from .evidence import compare_identities
from .models import (
    CONFIDENCE_ORDER,
    DuplicateCandidate,
    DuplicateConfidence,
    EvidenceComparison,
)


def classify_pair(
    comparison: EvidenceComparison,
) -> tuple[DuplicateConfidence | None, str]:
    """Return ``(confidence, rationale)`` for one comparison.

    Tiers:

    - ``definite`` — the same advertisement address or the same platform listing id
    - ``probable`` — same employer and role plus a corroborating facet
    - ``possible`` — one corroborating cluster only; needs owner judgment
    - ``None`` — not enough shared evidence to bother the owner
    """
    if comparison.matches("canonical_url"):
        return "definite", "Same canonical advertisement URL"
    if comparison.matches("source_url"):
        return "definite", "Same source advertisement URL"
    if comparison.matches("platform") and comparison.matches("platform_job_id"):
        return "definite", "Same platform and platform job id"

    company = comparison.matches("company")
    title = comparison.matches("title")
    location = comparison.matches("location")
    fingerprint = comparison.matches("content_fingerprint")

    if company and title and (location or fingerprint):
        corroboration = (
            "identical description text" if fingerprint else "same location"
        )
        return "probable", f"Same company and title with {corroboration}"
    if company and fingerprint:
        return "probable", "Same company with identical description text"
    if company and title:
        return "possible", "Same company and title, no corroborating facet"
    if fingerprint:
        return "possible", "Identical description text only"
    return None, "Insufficient shared evidence"


def build_candidate(
    left: Opportunity,
    right: Opportunity,
) -> DuplicateCandidate | None:
    """Compare two records and return an unresolved suggestion, if warranted.

    The pair is ordered by ``opportunity_id`` so scan order cannot change the
    result. ULIDs are time-sortable, so the first id is the earlier discovery.
    """
    first, second = sorted((left, right), key=lambda item: item.opportunity_id)
    comparison = compare_identities(first.identity, second.identity)
    confidence, rationale = classify_pair(comparison)
    if confidence is None:
        return None
    return DuplicateCandidate(
        opportunity_id=first.opportunity_id,
        other_opportunity_id=second.opportunity_id,
        confidence=confidence,
        rationale=rationale,
        comparison=comparison,
    )


def detect_candidates(records: list[Opportunity]) -> tuple[DuplicateCandidate, ...]:
    """All unresolved candidates across ``records``, strongest evidence first.

    Pairs the owner already settled are skipped: confirmed links, records already in
    the same confirmed group, and rejected suggestions. A rejected pair therefore
    never reappears, which is what makes repeated scans usable.
    """
    ordered = sorted(records, key=lambda item: item.opportunity_id)
    candidates: list[DuplicateCandidate] = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if _already_resolved(left, right):
                continue
            candidate = build_candidate(left, right)
            if candidate is not None:
                candidates.append(candidate)
    return tuple(sorted(candidates, key=_candidate_sort_key))


def _already_resolved(left: Opportunity, right: Opportunity) -> bool:
    if _is_rejected(left, right.opportunity_id) or _is_rejected(
        right, left.opportunity_id
    ):
        return True
    return _group_key(left) == _group_key(right)


def _group_key(record: Opportunity) -> str:
    if record.duplicate is not None:
        return record.duplicate.duplicate_of
    return record.opportunity_id


def _is_rejected(record: Opportunity, other_id: str) -> bool:
    return any(
        rejection.other_opportunity_id == other_id
        for rejection in record.duplicate_rejections
    )


def _candidate_sort_key(candidate: DuplicateCandidate) -> tuple[int, str, str]:
    return (
        CONFIDENCE_ORDER[candidate.confidence],
        candidate.opportunity_id,
        candidate.other_opportunity_id,
    )
