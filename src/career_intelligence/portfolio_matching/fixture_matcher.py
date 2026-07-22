"""Deterministic matcher used to exercise the service without ranking logic."""

from __future__ import annotations

from collections.abc import Callable

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

from .errors import PortfolioMatchingError
from .fixtures import MATCH_FIXTURE_BUILDERS
from .matcher import PortfolioMatchPayload

PayloadBuilder = Callable[[], PortfolioMatchPayload]


class FixtureMatcher:
    """Return canned portfolio-match payloads for representative job-analysis fixtures.

    Matching is intentionally dumb: distinctive fixture markers in
    ``job_analysis.posting.raw_text``. This is architecture test scaffolding, not
    intelligence. It is never a public default — callers (including tests) must pass
    it explicitly to PortfolioMatchingService.
    """

    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatchPayload:
        _ = profile
        builder = self._match(job_analysis)
        if builder is None:
            raise PortfolioMatchingError(
                "No fixture portfolio match is available for this job analysis. "
                "Provide a recognised fixture marker or a real matcher."
            )
        return builder()

    def _match(self, job_analysis: JobAnalysis) -> PayloadBuilder | None:
        raw_text = job_analysis.posting.raw_text
        for marker, builder in MATCH_FIXTURE_BUILDERS.items():
            if marker in raw_text:
                return builder
        return None
