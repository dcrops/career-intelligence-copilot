"""Deterministic assessor used to exercise the service without network access."""

from __future__ import annotations

from collections.abc import Callable

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

from .assessor import OpportunityAssessmentPayload
from .errors import OpportunityAssessmentError
from .fixtures import ASSESSMENT_FIXTURE_BUILDERS

PayloadBuilder = Callable[[], OpportunityAssessmentPayload]


class FixtureAssessor:
    """Return canned assessment payloads for representative job-analysis fixtures.

    Matching is intentionally dumb: distinctive fixture markers in
    ``job_analysis.posting.raw_text``. This is architecture test scaffolding, not
    intelligence. It is never a public default — callers (including tests) must pass
    it explicitly to OpportunityAssessmentService.
    """

    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        _ = profile
        builder = self._match(job_analysis)
        if builder is None:
            raise OpportunityAssessmentError(
                "No fixture assessment is available for this job analysis. "
                "Provide a recognised fixture marker or a real assessor."
            )
        return builder()

    def _match(self, job_analysis: JobAnalysis) -> PayloadBuilder | None:
        raw_text = job_analysis.posting.raw_text
        for marker, builder in ASSESSMENT_FIXTURE_BUILDERS.items():
            if marker in raw_text:
                return builder
        return None
