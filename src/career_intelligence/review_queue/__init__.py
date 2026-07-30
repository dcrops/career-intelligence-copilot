"""Public API for the derived opportunity review queue (FR-009 M1).

The queue is a projection, not a second system of record: Opportunities remain
the durable business data (ADR-004) and this package only reads and orders them.
"""

from .eligibility import evaluate_eligibility
from .models import (
    EXCLUSION_REASONS,
    QUEUE_SCOPES,
    ExclusionReason,
    QueueEligibility,
    QueueScope,
    ReviewQueue,
)
from .service import ReviewQueueService

__all__ = [
    "EXCLUSION_REASONS",
    "QUEUE_SCOPES",
    "ExclusionReason",
    "QueueEligibility",
    "QueueScope",
    "ReviewQueue",
    "ReviewQueueService",
    "evaluate_eligibility",
]
