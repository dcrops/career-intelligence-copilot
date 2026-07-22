"""Internal assessment schema for FR-003 AI-backed assessors.

``OpportunityAssessmentExtraction`` is the structured-output contract for assessors.
It intentionally excludes ``job_analysis`` and any caller-owned profile binding —
the service alone binds trusted inputs after assessment. Nested domain types are
reused; they are not duplicated here.
"""

from __future__ import annotations

from .models import (
    AssessmentModel,
    AssessmentSummary,
    FitDimensionAssessment,
)


class OpportunityAssessmentExtraction(AssessmentModel):
    """Fields an assessor may produce. Excludes ``job_analysis`` by design."""

    technical_fit: FitDimensionAssessment
    commercial_fit: FitDimensionAssessment
    portfolio_fit: FitDimensionAssessment
    summary: AssessmentSummary
