"""Validate CoverLetterPlan references against strategy and profile."""

from __future__ import annotations

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.profile.models import CareerProfile

from .errors import CoverLetterPlanValidationError, ErrorDetail
from .models import CoverLetterPlan


def validate_plan_references(
    plan: CoverLetterPlan,
    strategy: ApplicationStrategy,
    profile: CareerProfile,
) -> None:
    """Reject plans that cite unknown projects or drift from strategy identity."""
    errors: list[ErrorDetail] = []

    if plan.job_analysis.posting != strategy.job_analysis.posting:
        errors.append(
            ErrorDetail(
                loc=("job_analysis", "posting"),
                msg="CoverLetterPlan posting must match ApplicationStrategy posting",
                type="value_error",
            )
        )

    if plan.application_tier != strategy.application_tier:
        errors.append(
            ErrorDetail(
                loc=("application_tier",),
                msg="application_tier must match ApplicationStrategy",
                type="value_error",
            )
        )

    if plan.pursuit_posture != strategy.pursuit_posture:
        errors.append(
            ErrorDetail(
                loc=("pursuit_posture",),
                msg="pursuit_posture must match ApplicationStrategy",
                type="value_error",
            )
        )

    profile_project_ids = {project.id for project in profile.projects}
    for index, project in enumerate(plan.strongest_projects):
        if project.project_id not in profile_project_ids:
            errors.append(
                ErrorDetail(
                    loc=("strongest_projects", index, "project_id"),
                    msg=f"unknown project_id '{project.project_id}'",
                    type="value_error",
                )
            )

    for index, item in enumerate(plan.relevant_evidence):
        if item.project_id is not None and item.project_id not in profile_project_ids:
            errors.append(
                ErrorDetail(
                    loc=("relevant_evidence", index, "project_id"),
                    msg=f"unknown project_id '{item.project_id}'",
                    type="value_error",
                )
            )

    if errors:
        raise CoverLetterPlanValidationError(errors)
