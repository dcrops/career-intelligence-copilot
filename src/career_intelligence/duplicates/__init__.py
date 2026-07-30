"""Duplicate detection and duplicate group projections (FR-009 M3).

Detection is derived and advisory. Owner-confirmed outcomes are persisted on the
Opportunity aggregate through
``career_intelligence.opportunities.DuplicateReviewService``. Records are linked,
never merged or deleted.
"""

from .canonical import metadata_completeness, recommend_canonical
from .detection import build_candidate, classify_pair, detect_candidates
from .evidence import (
    compare_identities,
    location_tokens,
    normalise_company,
    normalise_title,
    normalise_url,
)
from .groups import build_groups, group_for
from .models import (
    CONFIDENCE_ORDER,
    DUPLICATE_CONFIDENCES,
    EVIDENCE_SIGNALS,
    CanonicalRecommendation,
    DuplicateCandidate,
    DuplicateCandidateReport,
    DuplicateConfidence,
    DuplicateGroup,
    EvidenceComparison,
    EvidenceSignal,
)
from .service import DuplicateDetectionService

__all__ = [
    "CONFIDENCE_ORDER",
    "DUPLICATE_CONFIDENCES",
    "EVIDENCE_SIGNALS",
    "CanonicalRecommendation",
    "DuplicateCandidate",
    "DuplicateCandidateReport",
    "DuplicateConfidence",
    "DuplicateDetectionService",
    "DuplicateGroup",
    "EvidenceComparison",
    "EvidenceSignal",
    "build_candidate",
    "build_groups",
    "classify_pair",
    "compare_identities",
    "detect_candidates",
    "group_for",
    "location_tokens",
    "metadata_completeness",
    "normalise_company",
    "normalise_title",
    "normalise_url",
    "recommend_canonical",
]
