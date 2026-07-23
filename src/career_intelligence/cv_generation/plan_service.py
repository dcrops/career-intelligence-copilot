"""Public trust boundary for TailoringPlan (FR-006 Phase A)."""

from __future__ import annotations

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.profile.models import CareerProfile

from .errors import (
    ErrorDetail,
    TailoringPlanGateError,
    TailoringPlanValidationError,
)
from .models import TailoringPlan
from .options import TailoringOptions
from .plan_refs import validate_plan_references
from .planner import TailoringPlanPayload, TailoringPlanner

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


class TailoringPlanService:
    """Stable interface for producing a trusted TailoringPlan.

    The service is the public trust boundary: it gates owner approval and
    material benefit, obtains an untrusted payload from an explicitly supplied
    planner, binds JobAnalysis from ApplicationStrategy, validates evidence
    references, and returns a trusted TailoringPlan.

    Callers must supply a planner — there is no production default.
    """

    def __init__(self, planner: TailoringPlanner) -> None:
        self._planner = planner

    def plan(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        *,
        options: TailoringOptions | None = None,
    ) -> TailoringPlan:
        resolved = options or TailoringOptions()
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
        options: TailoringOptions,
    ) -> None:
        if not options.owner_approved_to_tailor:
            raise TailoringPlanGateError(
                "owner_approved_to_tailor must be True before producing a "
                "TailoringPlan"
            )

        if options.override_material_benefit:
            return

        if strategy.application_tier in _MATERIAL_BENEFIT_TIERS:
            return

        if any(action.kind == "consider_cv_tailoring" for action in strategy.next_actions):
            return

        raise TailoringPlanGateError(
            "Material-benefit gate refused TailoringPlan: application_tier is "
            f"'{strategy.application_tier}' and next_actions does not include "
            "consider_cv_tailoring. Set override_material_benefit=True to proceed "
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
                            "the service binds caller-supplied trusted inputs"
                        ),
                        type="value_error",
                    )
                )
        if errors:
            raise TailoringPlanValidationError(errors)

    def _validate(self, payload: TailoringPlanPayload) -> TailoringPlan:
        try:
            return TailoringPlan.model_validate(payload)
        except ValidationError as error:
            raise TailoringPlanValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
