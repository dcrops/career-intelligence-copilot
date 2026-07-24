"""Fidelity checks: TailoredCv must faithfully reflect an approved TailoringPlan."""

from __future__ import annotations

from career_intelligence.cv_generation.errors import (
    CvGenerationValidationError,
    ErrorDetail,
)
from career_intelligence.cv_generation.models import TailoredCv, TailoringPlan


def validate_fidelity(cv: TailoredCv, plan: TailoringPlan) -> None:
    """Fail closed when rendered CV silently ignores or reorders the plan.

    Covers plan-owned sections only: projects, skills, experience guidance,
    and summary themes. Certifications are a fixed profile baseline
    (``certifications_source``) and are intentionally outside TailoringPlan
    fidelity — see ``baseline.active_certifications_baseline``.
    """
    errors: list[ErrorDetail] = []

    planned_project_ids = [item.project_id for item in plan.projects_to_emphasise]
    rendered_project_ids = [item.project_id for item in cv.projects]
    if rendered_project_ids != planned_project_ids:
        errors.append(
            ErrorDetail(
                loc=("projects",),
                msg=(
                    "rendered project order must exactly match "
                    f"TailoringPlan.projects_to_emphasise; "
                    f"plan={planned_project_ids}, cv={rendered_project_ids}"
                ),
                type="value_error",
            )
        )

    planned_promote = [item.skill_name for item in plan.skills_to_promote]
    planned_not = [item.skill_name for item in plan.skills_not_emphasised]
    emphasised = [item.skill_name for item in cv.skills if item.emphasised]
    deprioritised = [item.skill_name for item in cv.skills if not item.emphasised]

    if emphasised != planned_promote:
        errors.append(
            ErrorDetail(
                loc=("skills",),
                msg=(
                    "emphasised skills must exactly match "
                    f"TailoringPlan.skills_to_promote order; "
                    f"plan={planned_promote}, cv={emphasised}"
                ),
                type="value_error",
            )
        )

    if deprioritised != planned_not:
        errors.append(
            ErrorDetail(
                loc=("skills",),
                msg=(
                    "non-emphasised skills must exactly match "
                    f"TailoringPlan.skills_not_emphasised order; "
                    f"plan={planned_not}, cv={deprioritised}"
                ),
                type="value_error",
            )
        )

    planned_experience = list(plan.experience_guidance.included_experience_ids)
    rendered_experience = [item.experience_id for item in cv.experience]
    if rendered_experience != planned_experience:
        errors.append(
            ErrorDetail(
                loc=("experience",),
                msg=(
                    "rendered experience ids must exactly match "
                    "TailoringPlan.experience_guidance.included_experience_ids; "
                    f"plan={planned_experience}, cv={rendered_experience}"
                ),
                type="value_error",
            )
        )

    if cv.experience_guidance_kind != plan.experience_guidance.kind:
        errors.append(
            ErrorDetail(
                loc=("experience_guidance_kind",),
                msg=(
                    "experience_guidance_kind must match the TailoringPlan "
                    f"({plan.experience_guidance.kind})"
                ),
                type="value_error",
            )
        )

    planned_themes = [item.theme for item in plan.summary_themes]
    if list(cv.summary_themes) != planned_themes:
        errors.append(
            ErrorDetail(
                loc=("summary_themes",),
                msg=(
                    "summary_themes must match the TailoringPlan; "
                    f"plan={planned_themes}, cv={list(cv.summary_themes)}"
                ),
                type="value_error",
            )
        )

    # Markdown must mention promoted skills and lead project when present.
    markdown_folded = cv.rendered_markdown.casefold()
    for skill_name in planned_promote:
        if skill_name.casefold() not in markdown_folded:
            errors.append(
                ErrorDetail(
                    loc=("rendered_markdown",),
                    msg=(
                        f"rendered Markdown must emphasise promoted skill "
                        f"'{skill_name}'"
                    ),
                    type="value_error",
                )
            )

    if cv.projects:
        lead_name = cv.projects[0].name
        heading_needle = f"### {lead_name}".casefold()
        if heading_needle not in markdown_folded:
            errors.append(
                ErrorDetail(
                    loc=("rendered_markdown",),
                    msg=(
                        "rendered Markdown must lead with the first emphasised "
                        f"project heading '### {lead_name}'"
                    ),
                    type="value_error",
                )
            )
        # First project heading occurrence should be the lead project.
        heading_positions = [
            (markdown_folded.find(f"### {project.name}".casefold()), project.name)
            for project in cv.projects
        ]
        heading_positions = [
            (pos, name) for pos, name in heading_positions if pos >= 0
        ]
        if heading_positions:
            heading_positions.sort(key=lambda item: item[0])
            if heading_positions[0][1] != lead_name:
                errors.append(
                    ErrorDetail(
                        loc=("rendered_markdown",),
                        msg=(
                            "first emphasised project heading in Markdown must "
                            f"be the plan's rank-1 project '{lead_name}', found "
                            f"'{heading_positions[0][1]}' first"
                        ),
                        type="value_error",
                    )
                )

    if errors:
        raise CvGenerationValidationError(errors)
