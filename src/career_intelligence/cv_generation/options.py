"""Caller options for FR-006 Tailoring Plan and CV generation."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class OptionsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TailoringOptions(OptionsModel):
    """Inputs that gate and scope TailoringPlan production.

    ``owner_approved_to_tailor`` is the explicit decision to produce a Tailoring
    Plan for this opportunity. It is distinct from ``tailoring_plan_approved``
    (accept the plan before rendering) and from final CV owner review.
    """

    owner_approved_to_tailor: bool = False
    include_extended_history: bool = False
    override_material_benefit: bool = False


class ContactDetails(OptionsModel):
    """Optional caller-supplied contact overlay. Never invented from the profile."""

    email: NonEmptyString | None = None
    phone: NonEmptyString | None = None
    location: NonEmptyString | None = None
    linkedin_url: NonEmptyString | None = None
    portfolio_url: NonEmptyString | None = None
    github_url: NonEmptyString | None = None


class CvGenerationOptions(OptionsModel):
    """Inputs that gate CV rendering from an approved Tailoring Plan.

    ``tailoring_plan_approved`` is the explicit acceptance of the Tailoring Plan
    before rendering. It is distinct from ``owner_approved_to_tailor`` and from
    mandatory final review of the generated CV (``owner_review_required``).

    ``rewrite_summary`` opts into Phase C summary rewriting when a
    ``SummaryRewriter`` is injected into ``CvGenerationService``. Default False
    preserves Phase B profile-summary copy until manual validation completes.
    """

    tailoring_plan_approved: bool = False
    rewrite_summary: bool = False
    contact: ContactDetails | None = None
