"""Internal planning boundary for FR-005.

Kept package-private: consumers obtain strategies only through
ApplicationStrategyService.

Planner output is an untrusted structured payload. The service alone validates,
binds the caller-supplied JobAnalysis, and checks evidence references against
the caller-supplied trusted artifacts.
"""

from collections.abc import Mapping
from typing import Any, Protocol, TypeAlias

from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile

from .context import SearchOperatingContext

ApplicationStrategyPayload: TypeAlias = Mapping[str, Any]


class StrategyPlanner(Protocol):
    """Single-responsibility seam: produce application-strategy fields.

    The payload must describe generated strategy fields only. It must not include
    ``job_analysis``, ``profile``, ``career_profile``, ``opportunity_assessment``,
    ``portfolio_match``, ``operating_context``, or other caller-owned inputs —
    the service binds the caller-supplied trusted objects.
    """

    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        operating_context: SearchOperatingContext,
    ) -> ApplicationStrategyPayload:
        """Return untrusted application-strategy fields for the given inputs."""
