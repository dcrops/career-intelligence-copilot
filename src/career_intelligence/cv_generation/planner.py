"""Internal planning boundary for FR-006 TailoringPlan.

Kept package-private: consumers obtain plans only through TailoringPlanService.

Planner output is an untrusted structured payload. The service alone validates,
binds the caller-supplied JobAnalysis from ApplicationStrategy, and checks
evidence references.
"""

from collections.abc import Mapping
from typing import Any, Protocol, TypeAlias

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.profile.models import CareerProfile

from .options import TailoringOptions

TailoringPlanPayload: TypeAlias = Mapping[str, Any]


class TailoringPlanner(Protocol):
    """Produce TailoringPlan fields without binding trusted JobAnalysis."""

    def plan(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        options: TailoringOptions,
    ) -> TailoringPlanPayload:
        """Return untrusted TailoringPlan fields for the given trusted inputs."""
