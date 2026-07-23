"""Referential integrity checks for TailoringPlan evidence references."""

from __future__ import annotations

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

from .errors import ErrorDetail, TailoringPlanValidationError
from .models import JobEvidenceRef, PlanEvidenceRef, ProfileEvidenceRef, TailoringPlan

_LIST_JOB_SOURCES: dict[str, str] = {
    "technology": "technologies",
    "responsibility": "responsibilities",
    "experience_requirement": "experience_requirements",
}


def validate_plan_references(
    plan: TailoringPlan,
    strategy: ApplicationStrategy,
    profile: CareerProfile,
) -> None:
    """Ensure TailoringPlan evidence and entity ids resolve against trusted inputs."""
    errors: list[ErrorDetail] = []
    job = plan.job_analysis
    profile_project_ids = {project.id for project in profile.projects}
    profile_experience_ids = {entry.id for entry in profile.experience}
    skill_names = {
        skill.name.casefold()
        for skill in (
            *profile.skills.technical,
            *profile.skills.domain,
            *profile.skills.soft,
        )
    }
    emphasis_ids = [item.project_id for item in strategy.portfolio_emphasis]

    for index, priority in enumerate(plan.jd_priorities):
        for evidence_index, evidence in enumerate(priority.evidence):
            _validate_evidence(
                evidence,
                job,
                profile_project_ids,
                skill_names,
                ("jd_priorities", index, "evidence", evidence_index),
                errors,
            )

    for index, project in enumerate(plan.projects_to_emphasise):
        if project.project_id not in profile_project_ids:
            errors.append(
                ErrorDetail(
                    loc=("projects_to_emphasise", index, "project_id"),
                    msg=(
                        f"project_id '{project.project_id}' is absent from the "
                        "career profile"
                    ),
                    type="value_error",
                )
            )
        if project.project_id not in emphasis_ids:
            errors.append(
                ErrorDetail(
                    loc=("projects_to_emphasise", index, "project_id"),
                    msg=(
                        f"project_id '{project.project_id}' is not present in "
                        "ApplicationStrategy.portfolio_emphasis; the Tailoring "
                        "Plan must not invent project ranking"
                    ),
                    type="value_error",
                )
            )
        # Order must follow strategy portfolio_emphasis order among included ids.
        for evidence_index, evidence in enumerate(project.evidence):
            _validate_evidence(
                evidence,
                job,
                profile_project_ids,
                skill_names,
                ("projects_to_emphasise", index, "evidence", evidence_index),
                errors,
            )

    _validate_project_order(plan, emphasis_ids, errors)

    for index, skill in enumerate(plan.skills_to_promote):
        if skill.skill_name.casefold() not in skill_names:
            errors.append(
                ErrorDetail(
                    loc=("skills_to_promote", index, "skill_name"),
                    msg=(
                        f"skill_name '{skill.skill_name}' is absent from the "
                        "career profile"
                    ),
                    type="value_error",
                )
            )
        for evidence_index, evidence in enumerate(skill.evidence):
            _validate_evidence(
                evidence,
                job,
                profile_project_ids,
                skill_names,
                ("skills_to_promote", index, "evidence", evidence_index),
                errors,
            )

    for index, skill in enumerate(plan.skills_not_emphasised):
        if skill.skill_name.casefold() not in skill_names:
            errors.append(
                ErrorDetail(
                    loc=("skills_not_emphasised", index, "skill_name"),
                    msg=(
                        f"skill_name '{skill.skill_name}' is absent from the "
                        "career profile"
                    ),
                    type="value_error",
                )
            )

    for index, theme in enumerate(plan.summary_themes):
        for evidence_index, evidence in enumerate(theme.evidence):
            _validate_evidence(
                evidence,
                job,
                profile_project_ids,
                skill_names,
                ("summary_themes", index, "evidence", evidence_index),
                errors,
            )

    guidance = plan.experience_guidance
    for index, experience_id in enumerate(guidance.included_experience_ids):
        if experience_id not in profile_experience_ids:
            errors.append(
                ErrorDetail(
                    loc=("experience_guidance", "included_experience_ids", index),
                    msg=f"experience id '{experience_id}' is absent from the profile",
                    type="value_error",
                )
            )
    for index, experience_id in enumerate(guidance.excluded_experience_ids):
        if experience_id not in profile_experience_ids:
            errors.append(
                ErrorDetail(
                    loc=("experience_guidance", "excluded_experience_ids", index),
                    msg=f"experience id '{experience_id}' is absent from the profile",
                    type="value_error",
                )
            )

    covered = set(guidance.included_experience_ids) | set(
        guidance.excluded_experience_ids
    )
    if covered != profile_experience_ids:
        errors.append(
            ErrorDetail(
                loc=("experience_guidance",),
                msg=(
                    "experience_guidance must partition every profile experience "
                    "id into included or excluded"
                ),
                type="value_error",
            )
        )

    if errors:
        raise TailoringPlanValidationError(errors)


def _validate_project_order(
    plan: TailoringPlan,
    emphasis_ids: list[str],
    errors: list[ErrorDetail],
) -> None:
    planned_ids = [project.project_id for project in plan.projects_to_emphasise]
    expected = [project_id for project_id in emphasis_ids if project_id in planned_ids]
    # Planned ids must be a subsequence of strategy emphasis order.
    emphasis_index = 0
    for planned_id in planned_ids:
        try:
            emphasis_index = emphasis_ids.index(planned_id, emphasis_index) + 1
        except ValueError:
            errors.append(
                ErrorDetail(
                    loc=("projects_to_emphasise",),
                    msg=(
                        "projects_to_emphasise order must follow "
                        "ApplicationStrategy.portfolio_emphasis order; "
                        f"got {planned_ids}, emphasis {emphasis_ids}"
                    ),
                    type="value_error",
                )
            )
            return
    if planned_ids != expected and planned_ids:
        # If we skipped unknown ids, expected filters to planned only in emphasis order
        pass


def _validate_evidence(
    evidence: PlanEvidenceRef,
    job: JobAnalysis,
    profile_project_ids: set[str],
    skill_names: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if evidence.origin == "job_analysis" and evidence.job_evidence is not None:
        _validate_job_evidence(evidence.job_evidence, job, loc, errors)
    elif evidence.origin == "career_profile" and evidence.profile_evidence is not None:
        _validate_profile_evidence(
            evidence.profile_evidence, profile_project_ids, skill_names, loc, errors
        )
    elif evidence.origin == "application_strategy":
        if (
            evidence.portfolio_project_id is not None
            and evidence.portfolio_project_id not in profile_project_ids
        ):
            errors.append(
                ErrorDetail(
                    loc=(*loc, "portfolio_project_id"),
                    msg=(
                        f"portfolio_project_id '{evidence.portfolio_project_id}' "
                        "is absent from the career profile"
                    ),
                    type="value_error",
                )
            )


def _validate_job_evidence(
    ref: JobEvidenceRef,
    job: JobAnalysis,
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if ref.source in _LIST_JOB_SOURCES:
        attr = _LIST_JOB_SOURCES[ref.source]
        items = getattr(job, attr)
        if ref.item_index is None or ref.item_index >= len(items):
            errors.append(
                ErrorDetail(
                    loc=(*loc, "job_evidence", "item_index"),
                    msg=(
                        f"{ref.source} item_index {ref.item_index} is out of range "
                        f"for job_analysis.{attr}"
                    ),
                    type="value_error",
                )
            )
            return
        if ref.source == "technology" and ref.name is not None:
            actual = items[ref.item_index].name
            if actual.casefold() != ref.name.casefold():
                errors.append(
                    ErrorDetail(
                        loc=(*loc, "job_evidence", "name"),
                        msg=(
                            f"technology evidence name '{ref.name}' does not match "
                            f"job_analysis.technologies[{ref.item_index}].name "
                            f"'{actual}'"
                        ),
                        type="value_error",
                    )
                )


def _validate_profile_evidence(
    ref: ProfileEvidenceRef,
    profile_project_ids: set[str],
    skill_names: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if ref.source == "skill":
        prefix = "skill:"
        if not ref.ref.startswith(prefix):
            errors.append(
                ErrorDetail(
                    loc=(*loc, "profile_evidence", "ref"),
                    msg="skill profile evidence ref must use skill:<name>",
                    type="value_error",
                )
            )
            return
        name = ref.ref[len(prefix) :]
        if name.casefold() not in skill_names:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "profile_evidence", "ref"),
                    msg=f"skill ref '{ref.ref}' is absent from the career profile",
                    type="value_error",
                )
            )
    elif ref.source == "project":
        prefix = "project:"
        if not ref.ref.startswith(prefix):
            errors.append(
                ErrorDetail(
                    loc=(*loc, "profile_evidence", "ref"),
                    msg="project profile evidence ref must use project:<id>",
                    type="value_error",
                )
            )
            return
        project_id = ref.ref[len(prefix) :]
        if project_id not in profile_project_ids:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "profile_evidence", "ref"),
                    msg=f"project ref '{ref.ref}' is absent from the career profile",
                    type="value_error",
                )
            )
