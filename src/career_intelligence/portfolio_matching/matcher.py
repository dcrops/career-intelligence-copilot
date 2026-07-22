"""Internal matching boundary for FR-004.

Kept package-private: consumers obtain matches only through
PortfolioMatchingService.

Matcher output is an untrusted structured payload. The service alone validates,
binds the caller-supplied JobAnalysis, and checks project evidence references
against the caller-supplied CareerProfile.
"""

from collections.abc import Mapping
from typing import Any, Protocol, TypeAlias

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

PortfolioMatchPayload: TypeAlias = Mapping[str, Any]


class PortfolioMatcher(Protocol):
    """Single-responsibility seam: rank portfolio projects for a job analysis.

    The payload must describe generated match fields only. It must not include
    ``job_analysis``, ``profile``, or other caller-owned inputs — the service
    binds the caller-supplied trusted objects.
    """

    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatchPayload:
        """Return untrusted portfolio-match fields for the given inputs."""
