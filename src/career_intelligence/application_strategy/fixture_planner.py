"""Deterministic planner used to exercise the service without recommendation policy."""

from __future__ import annotations

from collections.abc import Callable

from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile

from .context import SearchOperatingContext
from .errors import ApplicationStrategyError
from .fixtures import (
    STRATEGY_FIXTURE_BUILDERS,
    VOLUME_OVERRIDE_MARKERS,
    strategy_volume_low_fit,
)
from .planner import ApplicationStrategyPayload

PayloadBuilder = Callable[[], ApplicationStrategyPayload]


class FixtureStrategyPlanner:
    """Return canned strategy payloads for representative job-analysis fixtures.

    Matching is intentionally dumb: distinctive fixture markers in
    ``assessment.job_analysis.posting.raw_text``, with an optional volume override
    when ``operating_context.volume_applications_enabled`` is true.

    This is architecture test scaffolding, not intelligence. It is never a public
    default — callers (including tests) must pass it explicitly to
    ``ApplicationStrategyService``. Production behaviour remains
    ``DeterministicStrategyPlanner``.
    """

    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        operating_context: SearchOperatingContext,
    ) -> ApplicationStrategyPayload:
        _ = portfolio_match, profile
        raw_text = assessment.job_analysis.posting.raw_text

        if operating_context.volume_applications_enabled:
            for marker in VOLUME_OVERRIDE_MARKERS:
                if marker in raw_text:
                    return strategy_volume_low_fit()

        builder = self._match(raw_text)
        if builder is None:
            raise ApplicationStrategyError(
                "No fixture application strategy is available for this job analysis. "
                "Provide a recognised fixture marker or a real planner."
            )
        return builder()

    def _match(self, raw_text: str) -> PayloadBuilder | None:
        for marker, builder in STRATEGY_FIXTURE_BUILDERS.items():
            if marker in raw_text:
                return builder
        return None
