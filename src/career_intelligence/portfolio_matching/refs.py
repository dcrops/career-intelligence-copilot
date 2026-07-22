"""Referential integrity checks for portfolio-match evidence references."""

from __future__ import annotations

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

from .errors import ErrorDetail, PortfolioMatchingValidationError
from .models import JobEvidenceRef, PortfolioMatch, ProfileEvidenceRef, RankedPortfolioProject

_LIST_JOB_SOURCES: dict[str, str] = {
    "technology": "technologies",
    "responsibility": "responsibilities",
    "experience_requirement": "experience_requirements",
}


def validate_references(match: PortfolioMatch, profile: CareerProfile) -> None:
    """Ensure project coverage and evidence refs resolve against bound inputs."""
    errors: list[ErrorDetail] = []

    profile_ids = {entry.id for entry in profile.projects}
    ranked_ids = {entry.project_id for entry in match.ranked_projects}
    unranked_ids = set(match.unranked_project_ids)
    covered_ids = ranked_ids | unranked_ids

    missing = profile_ids - covered_ids
    if missing:
        errors.append(
            ErrorDetail(
                loc=("ranked_projects",),
                msg=(
                    "match must cover every profile project exactly once; "
                    f"missing project id(s): {sorted(missing)}"
                ),
                type="value_error",
            )
        )

    unknown = covered_ids - profile_ids
    if unknown:
        errors.append(
            ErrorDetail(
                loc=("ranked_projects",),
                msg=(
                    "match references project id(s) absent from the bound career "
                    f"profile: {sorted(unknown)}"
                ),
                type="value_error",
            )
        )

    for project_index, project in enumerate(match.ranked_projects):
        _validate_ranked_project(
            project,
            match.job_analysis,
            profile_ids,
            project_index,
            errors,
        )

    if errors:
        raise PortfolioMatchingValidationError(errors)


def _validate_ranked_project(
    project: RankedPortfolioProject,
    job_analysis: JobAnalysis,
    profile_ids: set[str],
    project_index: int,
    errors: list[ErrorDetail],
) -> None:
    base_loc: tuple[str | int, ...] = ("ranked_projects", project_index)
    expected_ref = f"project:{project.project_id}"

    for factor_index, factor in enumerate(project.factors):
        factor_loc = (*base_loc, "factors", factor_index)
        cites_own_project = False

        for job_index, job_ref in enumerate(factor.job_evidence):
            _validate_job_ref(
                job_ref,
                job_analysis,
                (*factor_loc, "job_evidence", job_index),
                errors,
            )

        for profile_index, profile_ref in enumerate(factor.profile_evidence):
            profile_loc = (*factor_loc, "profile_evidence", profile_index)
            _validate_profile_ref(profile_ref, profile_ids, profile_loc, errors)
            if profile_ref.ref == expected_ref:
                cites_own_project = True

        if not cites_own_project:
            errors.append(
                ErrorDetail(
                    loc=(*factor_loc, "profile_evidence"),
                    msg=(
                        f"ranking factor must cite profile evidence '{expected_ref}' "
                        f"for ranked project '{project.project_id}'"
                    ),
                    type="value_error",
                )
            )


def _validate_job_ref(
    ref: JobEvidenceRef,
    job_analysis: JobAnalysis,
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if ref.source in _LIST_JOB_SOURCES:
        list_name = _LIST_JOB_SOURCES[ref.source]
        items = getattr(job_analysis, list_name)
        if ref.item_index is None:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "item_index"),
                    msg=f"{ref.source} job evidence requires item_index",
                    type="value_error",
                )
            )
            return
        if ref.item_index >= len(items):
            errors.append(
                ErrorDetail(
                    loc=(*loc, "item_index"),
                    msg=(
                        f"{ref.source} item_index {ref.item_index} is out of range "
                        f"for {len(items)} {list_name} item(s)"
                    ),
                    type="value_error",
                )
            )
            return
        if ref.name is not None and ref.source == "technology":
            item_name = items[ref.item_index].name
            if item_name.casefold() != ref.name.casefold():
                errors.append(
                    ErrorDetail(
                        loc=(*loc, "name"),
                        msg=(
                            f"technology name '{ref.name}' does not match "
                            f"technologies[{ref.item_index}].name '{item_name}'"
                        ),
                        type="value_error",
                    )
                )


def _validate_profile_ref(
    ref: ProfileEvidenceRef,
    profile_ids: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    pointer = ref.ref
    if ":" not in pointer:
        errors.append(
            ErrorDetail(
                loc=(*loc, "ref"),
                msg=f"profile evidence ref must use namespace:id form, got '{pointer}'",
                type="value_error",
            )
        )
        return

    namespace, identifier = pointer.split(":", 1)
    if not identifier:
        errors.append(
            ErrorDetail(
                loc=(*loc, "ref"),
                msg=f"profile evidence ref must include an identifier, got '{pointer}'",
                type="value_error",
            )
        )
        return

    if ref.source == "project":
        if namespace != "project":
            errors.append(
                ErrorDetail(
                    loc=(*loc, "ref"),
                    msg=(
                        "profile evidence source 'project' requires ref namespace "
                        f"'project', got '{namespace}'"
                    ),
                    type="value_error",
                )
            )
            return
        if identifier not in profile_ids:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "ref"),
                    msg=f"unknown project id '{identifier}' in bound career profile",
                    type="value_error",
                )
            )
