"""Referential integrity checks for assessment evidence references."""

from __future__ import annotations

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile, Preferences

from .errors import ErrorDetail, OpportunityAssessmentValidationError
from .models import (
    FitDimensionAssessment,
    JobEvidenceRef,
    OpportunityAssessment,
    ProfileEvidenceRef,
)

_VALID_PREFERENCE_REFS = frozenset(
    {
        "locations",
        "employment_types",
        "salary_min",
        "salary_currency",
        "remote",
        "company_stages",
        "must_haves",
        "deal_breakers",
    }
)

_VALID_IDENTITY_REFS = frozenset({"full_name", "target_role", "summary"})

_VALID_GOAL_REFS = frozenset({"primary", "secondary", "horizon_notes"})

_LIST_JOB_SOURCES: dict[str, str] = {
    "technology": "technologies",
    "responsibility": "responsibilities",
    "experience_requirement": "experience_requirements",
}


def validate_references(
    assessment: OpportunityAssessment,
    profile: CareerProfile,
) -> None:
    """Ensure profile and job evidence refs resolve against bound inputs."""
    errors: list[ErrorDetail] = []

    for dimension_name, dimension in _iter_dimensions(assessment):
        for finding_index, finding in enumerate(dimension.findings):
            base_loc = (dimension_name, "findings", finding_index)
            for job_index, job_ref in enumerate(finding.job_evidence):
                _validate_job_ref(
                    job_ref,
                    assessment.job_analysis,
                    (*base_loc, "job_evidence", job_index),
                    errors,
                )
            for profile_index, profile_ref in enumerate(finding.profile_evidence):
                _validate_profile_ref(
                    profile_ref,
                    profile,
                    (*base_loc, "profile_evidence", profile_index),
                    errors,
                )

    if errors:
        raise OpportunityAssessmentValidationError(errors)


def _iter_dimensions(
    assessment: OpportunityAssessment,
) -> list[tuple[str, FitDimensionAssessment]]:
    return [
        ("technical_fit", assessment.technical_fit),
        ("commercial_fit", assessment.commercial_fit),
        ("portfolio_fit", assessment.portfolio_fit),
    ]


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
    profile: CareerProfile,
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

    if ref.source == "experience":
        if namespace != "experience":
            errors.append(_namespace_mismatch(loc, ref.source, namespace))
            return
        if not any(entry.id == identifier for entry in profile.experience):
            errors.append(_unknown_entity(loc, "experience", identifier))
        return

    if ref.source == "project":
        if namespace != "project":
            errors.append(_namespace_mismatch(loc, ref.source, namespace))
            return
        if not any(entry.id == identifier for entry in profile.projects):
            errors.append(_unknown_entity(loc, "project", identifier))
        return

    if ref.source == "certification":
        if namespace != "certification":
            errors.append(_namespace_mismatch(loc, ref.source, namespace))
            return
        if not any(entry.id == identifier for entry in profile.certifications):
            errors.append(_unknown_entity(loc, "certification", identifier))
        return

    if ref.source == "skill":
        if namespace != "skill":
            errors.append(_namespace_mismatch(loc, ref.source, namespace))
            return
        if not _skill_exists(profile, identifier):
            errors.append(_unknown_entity(loc, "skill", identifier))
        return

    if ref.source == "preference":
        if namespace != "preference":
            errors.append(_namespace_mismatch(loc, ref.source, namespace))
            return
        if identifier not in _VALID_PREFERENCE_REFS:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "ref"),
                    msg=(
                        f"unknown preference ref '{identifier}'; "
                        f"expected one of {sorted(_VALID_PREFERENCE_REFS)}"
                    ),
                    type="value_error",
                )
            )
        _ = Preferences.model_fields.get(identifier)
        return

    if ref.source == "goal":
        if namespace != "goal":
            errors.append(_namespace_mismatch(loc, ref.source, namespace))
            return
        if identifier not in _VALID_GOAL_REFS:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "ref"),
                    msg=(
                        f"unknown goal ref '{identifier}'; "
                        f"expected one of {sorted(_VALID_GOAL_REFS)}"
                    ),
                    type="value_error",
                )
            )
        return

    if ref.source == "identity":
        if namespace != "identity":
            errors.append(_namespace_mismatch(loc, ref.source, namespace))
            return
        if identifier not in _VALID_IDENTITY_REFS:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "ref"),
                    msg=(
                        f"unknown identity ref '{identifier}'; "
                        f"expected one of {sorted(_VALID_IDENTITY_REFS)}"
                    ),
                    type="value_error",
                )
            )
        return


def _skill_exists(profile: CareerProfile, name: str) -> bool:
    lowered = name.casefold()
    for bucket in (profile.skills.technical, profile.skills.domain, profile.skills.soft):
        if any(skill.name.casefold() == lowered for skill in bucket):
            return True
    return False


def _namespace_mismatch(
    loc: tuple[str | int, ...],
    source: str,
    namespace: str,
) -> ErrorDetail:
    return ErrorDetail(
        loc=(*loc, "ref"),
        msg=f"profile evidence source '{source}' requires ref namespace '{source}', got '{namespace}'",
        type="value_error",
    )


def _unknown_entity(
    loc: tuple[str | int, ...],
    entity: str,
    identifier: str,
) -> ErrorDetail:
    return ErrorDetail(
        loc=(*loc, "ref"),
        msg=f"unknown {entity} id '{identifier}' in bound career profile",
        type="value_error",
    )
