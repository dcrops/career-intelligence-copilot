"""Caller options for FR-007 Cover Letter Plan and generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from career_intelligence.cv_generation.options import ContactDetails


class OptionsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CoverLetterPlanOptions(OptionsModel):
    """Inputs that gate CoverLetterPlan production.

    ``owner_approved_to_plan`` is the explicit decision to produce a Cover Letter
    Plan for this opportunity. Distinct from ``cover_letter_plan_approved``
    (accept the plan before rendering) and from final owner review.
    """

    owner_approved_to_plan: bool = False
    override_material_benefit: bool = False


class CoverLetterGenerationOptions(OptionsModel):
    """Inputs that gate cover letter rendering from an approved plan.

    ``cover_letter_plan_approved`` is the explicit acceptance of the Cover Letter
    Plan before rendering. Final ``owner_review_required`` remains mandatory.

    ``contact`` supplies the header contact block (same ContactDetails shape as FR-006).
    """

    cover_letter_plan_approved: bool = False
    contact: ContactDetails | None = None
