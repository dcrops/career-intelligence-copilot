"""Shared pipeline constants (FR-013)."""

from __future__ import annotations

from career_intelligence.opportunities.models import PipelineStatus

# Owner-facing "active pipeline" — in-flight apply execution (not catalogue/assessed).
ACTIVE_PIPELINE_STATUSES: frozenset[PipelineStatus] = frozenset(
    {"preparing", "submitted", "interviewing", "offer"}
)
