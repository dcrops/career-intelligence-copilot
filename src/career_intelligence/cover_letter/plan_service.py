"""Public trust boundary for CoverLetterPlan (FR-007 Phase A)."""

from __future__ import annotations

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.profile.models import CareerProfile

from .errors import (
    CoverLetterPlanGateError,
    CoverLetterPlanValidationError,
    ErrorDetail,
)
from .models import CoverLetterPlan
from .options import CoverLetterPlanOptions
from .plan_refs import validate_plan_references
from .planner import CoverLetterPlanner

_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "job_analysis",
        "profile",
        "career_profile",
        "application_strategy",
        "opportunity_assessment",
        "portfolio_match",
    }
)

_MATERIAL_BENEFIT_TIERS = frozenset({"platinum", "gold"})


class CoverLetterPlanService:
    """Stable interface for producing a trusted CoverLetterPlan.

    Gates owner approval and material benefit, obtains an untrusted payload from
    an explicitly supplied planner, binds JobAnalysis from ApplicationStrategy,
    validates references, and returns a trusted CoverLetterPlan.
    """

    def __init__(self, planner: CoverLetterPlanner) -> None:
        self._planner = planner

    def plan(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        *,
        options: CoverLetterPlanOptions | None = None,
    ) -> CoverLetterPlan:
        resolved = options or CoverLetterPlanOptions()
        self._enforce_gates(strategy, resolved)

        payload = dict(self._planner.plan(strategy, profile, resolved))
        self._reject_embedded_inputs(payload)
        payload["job_analysis"] = strategy.job_analysis
        plan = self._validate(payload)
        validate_plan_references(plan, strategy, profile)
        return plan

    def _enforce_gates(
        self,
        strategy: ApplicationStrategy,
        options: CoverLetterPlanOptions,
    ) -> None:
        if not options.owner_approved_to_plan:
            raise CoverLetterPlanGateError(
                "owner_approved_to_plan must be True before producing a "
                "CoverLetterPlan"
            )

        if options.override_material_benefit:
            return

        if strategy.application_tier in _MATERIAL_BENEFIT_TIERS:
            return

        if any(action.kind == "consider_cover_letter" for action in strategy.next_actions):
            return

        raise CoverLetterPlanGateError(
            "Material-benefit gate refused CoverLetterPlan: application_tier is "
            f"'{strategy.application_tier}' and next_actions does not include "
            "consider_cover_letter. Set override_material_benefit=True to proceed "
            "with an explicit recorded override."
        )

    def _reject_embedded_inputs(self, payload: dict[str, object]) -> None:
        errors: list[ErrorDetail] = []
        for key in _FORBIDDEN_PAYLOAD_KEYS:
            if key in payload:
                errors.append(
                    ErrorDetail(
                        loc=(key,),
                        msg=(
                            f"planner payload must not include '{key}'; "
                            "the service binds JobAnalysis from ApplicationStrategy"
                        ),
                        type="value_error",
                    )
                )
        if errors:
            raise CoverLetterPlanValidationError(errors)

    def _validate(self, payload: dict[str, object]) -> CoverLetterPlan:
        try:
            return CoverLetterPlan.model_validate(payload)
        except ValidationError as error:
            raise CoverLetterPlanValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
