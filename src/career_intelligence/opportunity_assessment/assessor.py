"""Internal assessment boundary for FR-003.

Kept package-private: consumers obtain assessments only through
OpportunityAssessmentService.

Assessor output is an untrusted structured payload. The service alone validates,
binds the caller-supplied JobAnalysis, and checks profile evidence references
against the caller-supplied CareerProfile.
"""

from collections.abc import Mapping
from typing import Any, Protocol, TypeAlias

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

OpportunityAssessmentPayload: TypeAlias = Mapping[str, Any]


class Assessor(Protocol):
    """Single-responsibility seam: compare job analysis to profile.

    The payload must describe generated assessment fields only. It must not
    include ``job_analysis``, ``profile``, or other caller-owned inputs — the
    service binds the caller-supplied trusted objects.
    """

    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        """Return untrusted assessment fields for the given inputs."""
