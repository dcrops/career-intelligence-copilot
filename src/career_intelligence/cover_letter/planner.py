"""Package-private planner protocol for FR-007 Cover Letter Plan."""

from __future__ import annotations

from typing import Protocol, TypedDict

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.profile.models import CareerProfile

from .options import CoverLetterPlanOptions


class CoverLetterPlanPayload(TypedDict, total=False):
    """Untrusted planner output — JobAnalysis is bound by the service."""

    application_tier: str
    pursuit_posture: str
    company_alignment: dict[str, object]
    role_motivation: dict[str, object]
    relevant_evidence: list[dict[str, object]]
    strongest_projects: list[dict[str, object]]
    closing_strategy: dict[str, object]
    assumptions: list[str]
    insufficient_evidence: bool
    material_benefit_override: bool


class CoverLetterPlanner(Protocol):
    """Produces an untrusted CoverLetterPlan payload from strategy + profile."""

    def plan(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        options: CoverLetterPlanOptions,
    ) -> CoverLetterPlanPayload: ...
