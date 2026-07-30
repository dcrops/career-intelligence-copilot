"""Derived duplicate-review models (FR-009 M3).

Everything here is computed from persisted Opportunities and is never written back
to the store. Only owner outcomes (``DuplicateRelation``,
``Opportunity.duplicate_rejections``) are durable, exactly as queue position stays
derived in FR-009 M1/M2.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

DuplicateConfidence = Literal["definite", "probable", "possible"]
"""Deterministic strength of the evidence, never an automatic merge authority."""

DUPLICATE_CONFIDENCES: tuple[DuplicateConfidence, ...] = (
    "definite",
    "probable",
    "possible",
)

CONFIDENCE_ORDER: dict[DuplicateConfidence, int] = {
    confidence: index for index, confidence in enumerate(DUPLICATE_CONFIDENCES)
}

EvidenceSignal = Literal[
    "platform",
    "platform_job_id",
    "canonical_url",
    "source_url",
    "company",
    "title",
    "location",
    "content_fingerprint",
]
"""Comparable facets available on ``OpportunityIdentity`` today."""

EVIDENCE_SIGNALS: tuple[EvidenceSignal, ...] = (
    "platform",
    "platform_job_id",
    "canonical_url",
    "source_url",
    "company",
    "title",
    "location",
    "content_fingerprint",
)


class DuplicateModel(BaseModel):
    """Frozen base so derived projections cannot be mutated in place."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceComparison(DuplicateModel):
    """Facet-by-facet comparison of two candidate advertisements.

    ``unknown`` records facets missing on at least one side. Missing data is never
    treated as agreement — the acquisition audit found live records with no platform
    job id or canonical URL at all.
    """

    matching: tuple[EvidenceSignal, ...] = ()
    differing: tuple[EvidenceSignal, ...] = ()
    unknown: tuple[EvidenceSignal, ...] = ()

    def matches(self, signal: EvidenceSignal) -> bool:
        return signal in self.matching

    def differs(self, signal: EvidenceSignal) -> bool:
        return signal in self.differing


class DuplicateCandidate(DuplicateModel):
    """One unresolved suggestion that two records may be the same vacancy.

    ``opportunity_id`` / ``other_opportunity_id`` are ordered so the same pair always
    produces the same candidate regardless of scan order. Neither side is proposed as
    canonical here: canonical selection is a separate deterministic recommendation the
    owner confirms.
    """

    opportunity_id: str
    other_opportunity_id: str
    confidence: DuplicateConfidence
    rationale: str
    comparison: EvidenceComparison

    @property
    def pair(self) -> tuple[str, str]:
        return (self.opportunity_id, self.other_opportunity_id)


class DuplicateCandidateReport(DuplicateModel):
    """Deterministic set of unresolved duplicate suggestions at a point in time."""

    generated_at: datetime
    candidates: tuple[DuplicateCandidate, ...] = ()
    owner_confirmation_required: bool = True

    @property
    def pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(candidate.pair for candidate in self.candidates)


class DuplicateGroup(DuplicateModel):
    """Owner-confirmed set of advertisements for one real-world vacancy.

    Star-shaped: ``canonical_opportunity_id`` carries no relation and every id in
    ``member_opportunity_ids`` points at it. No record is deleted or collapsed, so
    provenance for each advertisement survives.
    """

    canonical_opportunity_id: str
    member_opportunity_ids: tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return 1 + len(self.member_opportunity_ids)

    @property
    def opportunity_ids(self) -> tuple[str, ...]:
        return (self.canonical_opportunity_id, *self.member_opportunity_ids)


class CanonicalRecommendation(DuplicateModel):
    """Deterministic canonical suggestion for a confirmed group.

    Advisory only. ``DuplicateReviewService.confirm_canonical`` still requires an
    explicit owner choice, so the recommendation can never silently re-point a group.
    """

    group_opportunity_ids: tuple[str, ...]
    recommended_opportunity_id: str
    current_canonical_opportunity_id: str
    reasons: tuple[str, ...] = ()
    owner_confirmation_required: bool = True

    @property
    def matches_current(self) -> bool:
        return self.recommended_opportunity_id == self.current_canonical_opportunity_id
