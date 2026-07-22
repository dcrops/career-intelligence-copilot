"""Referential integrity checks for application-strategy evidence references."""

from __future__ import annotations

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile, Preferences

from .errors import ErrorDetail, ApplicationStrategyValidationError
from .models import (
    ApplicationStrategy,
    JobEvidenceRef,
    ManualCheck,
    NextAction,
    PortfolioEmphasis,
    ProfileEvidenceRef,
    StrategyEvidenceRef,
    StrategyReason,
    StrategyRiskOrGap,
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

_DIMENSION_ATTR: dict[str, str] = {
    "technical": "technical_fit",
    "commercial": "commercial_fit",
    "portfolio": "portfolio_fit",
}


def validate_references(
    strategy: ApplicationStrategy,
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
) -> None:
    """Ensure strategy evidence refs resolve against caller-supplied trusted inputs."""
    errors: list[ErrorDetail] = []
    match_project_ids = _portfolio_project_ids(portfolio_match)
    profile_project_ids = {entry.id for entry in profile.projects}

    for index, reason in enumerate(strategy.reasons):
        _validate_reason(
            reason,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            ("reasons", index),
            errors,
        )

    for index, risk in enumerate(strategy.risks_or_gaps):
        _validate_risk(
            risk,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            ("risks_or_gaps", index),
            errors,
        )

    for index, check in enumerate(strategy.manual_checks):
        _validate_manual_check(
            check,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            ("manual_checks", index),
            errors,
        )

    for index, action in enumerate(strategy.next_actions):
        _validate_next_action(
            action,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            profile_project_ids,
            ("next_actions", index),
            errors,
        )

    for index, emphasis in enumerate(strategy.portfolio_emphasis):
        _validate_portfolio_emphasis(
            emphasis,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            profile_project_ids,
            ("portfolio_emphasis", index),
            errors,
        )

    if errors:
        raise ApplicationStrategyValidationError(errors)


def _portfolio_project_ids(portfolio_match: PortfolioMatch) -> set[str]:
    ranked = {entry.project_id for entry in portfolio_match.ranked_projects}
    return ranked | set(portfolio_match.unranked_project_ids)


def _validate_reason(
    reason: StrategyReason,
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
    match_project_ids: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    for evidence_index, evidence in enumerate(reason.evidence):
        _validate_strategy_evidence(
            evidence,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            (*loc, "evidence", evidence_index),
            errors,
        )


def _validate_risk(
    risk: StrategyRiskOrGap,
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
    match_project_ids: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    for evidence_index, evidence in enumerate(risk.evidence):
        _validate_strategy_evidence(
            evidence,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            (*loc, "evidence", evidence_index),
            errors,
        )


def _validate_manual_check(
    check: ManualCheck,
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
    match_project_ids: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    for evidence_index, evidence in enumerate(check.evidence):
        _validate_strategy_evidence(
            evidence,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            (*loc, "evidence", evidence_index),
            errors,
        )


def _validate_next_action(
    action: NextAction,
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
    match_project_ids: set[str],
    profile_project_ids: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    for evidence_index, evidence in enumerate(action.evidence):
        _validate_strategy_evidence(
            evidence,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            (*loc, "evidence", evidence_index),
            errors,
        )

    if action.related_project_id is None:
        return

    if action.related_project_id not in match_project_ids:
        errors.append(
            ErrorDetail(
                loc=(*loc, "related_project_id"),
                msg=(
                    f"related_project_id '{action.related_project_id}' is not present "
                    "in the supplied PortfolioMatch"
                ),
                type="value_error",
            )
        )
    if action.related_project_id not in profile_project_ids:
        errors.append(
            ErrorDetail(
                loc=(*loc, "related_project_id"),
                msg=(
                    f"related_project_id '{action.related_project_id}' is absent "
                    "from the bound career profile"
                ),
                type="value_error",
            )
        )


def _validate_portfolio_emphasis(
    emphasis: PortfolioEmphasis,
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
    match_project_ids: set[str],
    profile_project_ids: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if emphasis.project_id not in match_project_ids:
        errors.append(
            ErrorDetail(
                loc=(*loc, "project_id"),
                msg=(
                    f"portfolio emphasis project_id '{emphasis.project_id}' is not "
                    "present in the supplied PortfolioMatch"
                ),
                type="value_error",
            )
        )
    if emphasis.project_id not in profile_project_ids:
        errors.append(
            ErrorDetail(
                loc=(*loc, "project_id"),
                msg=(
                    f"portfolio emphasis project_id '{emphasis.project_id}' is absent "
                    "from the bound career profile"
                ),
                type="value_error",
            )
        )

    if emphasis.source_rank is not None:
        ranked = {
            entry.project_id: entry.rank for entry in portfolio_match.ranked_projects
        }
        expected_rank = ranked.get(emphasis.project_id)
        if expected_rank is None:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "source_rank"),
                    msg=(
                        f"source_rank is set for unranked project "
                        f"'{emphasis.project_id}'"
                    ),
                    type="value_error",
                )
            )
        elif expected_rank != emphasis.source_rank:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "source_rank"),
                    msg=(
                        f"source_rank {emphasis.source_rank} does not match "
                        f"PortfolioMatch rank {expected_rank} for "
                        f"'{emphasis.project_id}'"
                    ),
                    type="value_error",
                )
            )

    for evidence_index, evidence in enumerate(emphasis.evidence):
        _validate_strategy_evidence(
            evidence,
            assessment,
            portfolio_match,
            profile,
            match_project_ids,
            (*loc, "evidence", evidence_index),
            errors,
        )


def _validate_strategy_evidence(
    evidence: StrategyEvidenceRef,
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
    match_project_ids: set[str],
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if evidence.origin == "job_analysis":
        assert evidence.job_evidence is not None
        _validate_job_ref(
            evidence.job_evidence,
            strategy_job_analysis=assessment.job_analysis,
            loc=(*loc, "job_evidence"),
            errors=errors,
        )
        return

    if evidence.origin == "career_profile":
        assert evidence.profile_evidence is not None
        _validate_profile_ref(
            evidence.profile_evidence,
            profile,
            (*loc, "profile_evidence"),
            errors,
        )
        return

    if evidence.origin == "opportunity_assessment":
        assert evidence.assessment_dimension is not None
        attr = _DIMENSION_ATTR[evidence.assessment_dimension]
        dimension = getattr(assessment, attr)
        if (
            evidence.assessment_judgment is not None
            and evidence.assessment_judgment != dimension.judgment
        ):
            errors.append(
                ErrorDetail(
                    loc=(*loc, "assessment_judgment"),
                    msg=(
                        f"assessment_judgment '{evidence.assessment_judgment}' does "
                        f"not match {attr}.judgment '{dimension.judgment}'"
                    ),
                    type="value_error",
                )
            )
        return

    if evidence.origin == "portfolio_match":
        assert evidence.portfolio_project_id is not None
        if evidence.portfolio_project_id not in match_project_ids:
            errors.append(
                ErrorDetail(
                    loc=(*loc, "portfolio_project_id"),
                    msg=(
                        f"portfolio_project_id '{evidence.portfolio_project_id}' is "
                        "not present in the supplied PortfolioMatch"
                    ),
                    type="value_error",
                )
            )
        _ = portfolio_match
        return


def _validate_job_ref(
    ref: JobEvidenceRef,
    strategy_job_analysis: JobAnalysis,
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if ref.source in _LIST_JOB_SOURCES:
        list_name = _LIST_JOB_SOURCES[ref.source]
        items = getattr(strategy_job_analysis, list_name)
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
        return

    if ref.item_index is not None:
        errors.append(
            ErrorDetail(
                loc=(*loc, "item_index"),
                msg=f"{ref.source} job evidence must omit item_index",
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
        msg=(
            f"profile evidence source '{source}' requires ref namespace "
            f"'{source}', got '{namespace}'"
        ),
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
