"""Functional acceptance tests for FR-005 Application Strategy (public service boundary)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import career_intelligence.application_strategy as strategy_api
import pytest
from career_intelligence.application_strategy import (
    ApplicationStrategy,
    ApplicationStrategyError,
    ApplicationStrategyService,
    ApplicationStrategyValidationError,
    SearchOperatingContext,
)
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.application_strategy.planner import ApplicationStrategyPayload
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile import CareerProfile, CareerProfileService

_FORBIDDEN_OUTPUT_FIELD_NAMES = frozenset(
    {
        "cover_letter_body",
        "cv_body",
        "cv_content",
        "outreach",
        "submit_application",
        "browser_automation",
        "interview_probability",
        "percentage",
        "score",
        "apply_decision",
        "system_apply",
        "system_skip",
    }
)


def _golden_profile(golden_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(golden_profile_path).load()


def _profile_with(
    golden_profile_path: Path,
    **preference_updates: Any,
) -> CareerProfile:
    profile = _golden_profile(golden_profile_path)
    preferences = profile.preferences.model_copy(update=preference_updates)
    return profile.model_copy(update={"preferences": preferences})


def _service() -> ApplicationStrategyService:
    return ApplicationStrategyService(DeterministicStrategyPlanner())


def _job_analysis(**overrides: object) -> JobAnalysis:
    payload: dict[str, object] = {
        "posting": {
            "raw_text": "Senior AI Engineer. Python required. Hybrid Melbourne.",
            "title": "Senior AI Engineer",
            "company": "Example AI Co",
        },
        "role_family": {
            "family": "ai_engineering",
            "evidence": [{"excerpt": "Senior AI Engineer", "section": "title"}],
        },
        "seniority": {
            "level": "senior",
            "ambiguous": False,
            "evidence": [{"excerpt": "Senior AI Engineer", "section": "title"}],
        },
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [{"excerpt": "Python required", "section": "requirements"}],
            }
        ],
        "responsibilities": [
            {
                "description": "Build LLM applications",
                "evidence": [
                    {
                        "excerpt": "Build LLM applications",
                        "section": "responsibilities",
                    }
                ],
            }
        ],
        "compensation": {"clarity": "unstated"},
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [{"excerpt": "Hybrid Melbourne", "section": "location"}],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "evidence": [{"excerpt": "Hybrid Melbourne", "section": "location"}],
        },
        "employment": {},
        "experience_requirements": [],
    }
    payload.update(overrides)
    return JobAnalysis.model_validate(payload)


def _finding(
    *,
    kind: str = "alignment",
    summary: str,
    importance: str = "material",
    job_evidence: list[dict[str, Any]] | None = None,
    profile_evidence: list[dict[str, Any]] | None = None,
    assumption: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": kind,
        "summary": summary,
        "importance": importance,
        "job_evidence": job_evidence
        or [{"source": "technology", "item_index": 0, "name": "Python"}],
        "profile_evidence": profile_evidence
        or [{"source": "skill", "ref": "skill:Python"}],
    }
    if kind == "assumption":
        payload["assumption"] = assumption or summary
        payload["job_evidence"] = []
        payload["profile_evidence"] = []
    elif kind == "gap":
        payload["profile_evidence"] = profile_evidence or []
    elif kind == "uncertainty":
        payload["job_evidence"] = job_evidence or [{"source": "compensation"}]
        payload["profile_evidence"] = profile_evidence or []
    return payload


def _dimension(
    dimension: str,
    judgment: str,
    summary: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "judgment": judgment,
        "summary": summary,
        "findings": findings,
    }


def _assessment_for(
    analysis: JobAnalysis,
    *,
    technical: dict[str, Any],
    commercial: dict[str, Any],
    portfolio: dict[str, Any],
    summary: str,
) -> OpportunityAssessment:
    return OpportunityAssessment.model_validate(
        {
            "job_analysis": analysis.model_dump(mode="json"),
            "technical_fit": technical,
            "commercial_fit": commercial,
            "portfolio_fit": portfolio,
            "summary": {
                "summary": summary,
                "key_alignments": [],
                "key_gaps": [],
            },
        }
    )


def _portfolio_match_for(
    analysis: JobAnalysis,
    *,
    project_id: str = "operational-intelligence-copilot",
    insufficient_evidence: bool = False,
    ranked: bool = True,
) -> PortfolioMatch:
    golden_ids = [
        "operational-intelligence-copilot",
        "governance-document-rag",
        "payroll-diagnostics-engine",
        "public-holiday-entitlements",
    ]
    if insufficient_evidence or not ranked:
        payload: dict[str, object] = {
            "job_analysis": analysis.model_dump(mode="json"),
            "ranked_projects": [],
            "unranked_project_ids": golden_ids,
            "summary": "Insufficient evidence to rank projects.",
            "insufficient_evidence": True,
        }
    else:
        remaining = [item for item in golden_ids if item != project_id]
        payload = {
            "job_analysis": analysis.model_dump(mode="json"),
            "ranked_projects": [
                {
                    "rank": 1,
                    "project_id": project_id,
                    "rationale": f"Lead with {project_id}.",
                    "factors": [
                        {
                            "kind": "required_technology",
                            "summary": f"{project_id} uses required Python.",
                            "job_evidence": [
                                {
                                    "source": "technology",
                                    "item_index": 0,
                                    "name": "Python",
                                }
                            ],
                            "profile_evidence": [
                                {
                                    "source": "project",
                                    "ref": f"project:{project_id}",
                                }
                            ],
                        }
                    ],
                }
            ],
            "unranked_project_ids": remaining,
            "summary": f"Lead with {project_id}.",
            "insufficient_evidence": False,
        }
    return PortfolioMatch.model_validate(payload)


def _plan(
    assessment: OpportunityAssessment,
    match: PortfolioMatch,
    profile: CareerProfile,
    *,
    operating_context: SearchOperatingContext | None = None,
) -> ApplicationStrategy:
    return _service().plan(
        assessment,
        match,
        profile,
        operating_context=operating_context,
    )


def _collect_field_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            names.add(str(key).lower())
            names |= _collect_field_names(nested)
    elif isinstance(value, list):
        for item in value:
            names |= _collect_field_names(item)
    return names


def _assert_five_questions(strategy: ApplicationStrategy) -> None:
    assert strategy.summary
    assert strategy.reasons
    assert all(reason.evidence for reason in strategy.reasons)
    assert strategy.next_actions
    assert all(action.kind.startswith("consider_") for action in strategy.next_actions)
    assert strategy.owner_review_required is True
    # risks/manual_checks/assumptions/blockers may be empty for strong cases,
    # but at least one of risks, checks, or assumptions should usually appear;
    # strong cases may have empty risks — still require reasons + next_actions + evidence.


def _assert_no_forbidden_fields(strategy: ApplicationStrategy) -> None:
    names = _collect_field_names(strategy.model_dump(mode="json"))
    present = names & _FORBIDDEN_OUTPUT_FIELD_NAMES
    assert not present, f"forbidden fields present: {sorted(present)}"
    dumped = strategy.model_dump(mode="json")
    assert "opportunity_assessment" not in dumped
    assert "portfolio_match" not in dumped
    assert "career_profile" not in dumped
    assert "profile" not in dumped


def test_public_api_exports_service_contract_only() -> None:
    assert hasattr(strategy_api, "ApplicationStrategyService")
    assert hasattr(strategy_api, "ApplicationStrategy")
    assert hasattr(strategy_api, "SearchOperatingContext")
    assert not hasattr(strategy_api, "DeterministicStrategyPlanner")
    assert not hasattr(strategy_api, "FixtureStrategyPlanner")


def test_service_requires_an_explicit_planner() -> None:
    with pytest.raises(TypeError):
        ApplicationStrategyService()  # type: ignore[call-arg]


def test_strong_ai_engineer_opportunity(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        compensation={
            "clarity": "stated",
            "minimum": 150000,
            "maximum": 180000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "$150,000-$180,000 AUD",
            "evidence": [{"excerpt": "$150,000-$180,000 AUD"}],
        },
        employment={
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [{"excerpt": "Full-time permanent"}],
        },
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical alignment.",
            [_finding(summary="Python and AI stack align.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit is acceptable.",
            [
                _finding(
                    summary="Melbourne hybrid aligns with preferences.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio strongly supports the role.",
            [
                _finding(
                    summary="Project supports AI engineering narrative.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Strong AI Engineer opportunity.",
    )
    strategy = _plan(
        assessment,
        _portfolio_match_for(analysis),
        profile,
    )

    assert strategy.pursuit_posture == "prioritise"
    assert strategy.application_tier == "platinum"
    assert strategy.effort_level == "full"
    assert strategy.practical_value == "career_priority"
    assert strategy.portfolio_emphasis
    assert any(
        action.kind == "consider_cv_tailoring" for action in strategy.next_actions
    )
    _assert_five_questions(strategy)
    _assert_no_forbidden_fields(strategy)


def test_applied_ai_mixed_commercial_fit(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        posting={
            "raw_text": "Applied AI Engineer. Python required. Hybrid Sydney.",
            "title": "Applied AI Engineer",
            "company": "Harbour Labs",
        },
        location={
            "clarity": "stated",
            "summary": "Sydney",
            "evidence": [{"excerpt": "Hybrid Sydney"}],
        },
        work_arrangement={
            "arrangement": "hybrid",
            "evidence": [{"excerpt": "Hybrid Sydney"}],
        },
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong applied AI technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "mixed",
            "Mixed commercial fit due to Sydney hybrid expectations.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Sydney hybrid creates commercial friction.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "moderate",
            "Portfolio supports applied AI narrative.",
            [
                _finding(
                    summary="Project evidence is usable.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Applied AI with mixed commercial fit.",
    )
    strategy = _plan(assessment, _portfolio_match_for(analysis), profile)

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.application_tier in {"gold", "silver"}
    assert strategy.pursuit_posture != "do_not_prioritise"
    assert any("commercial" in risk.summary.casefold() for risk in strategy.risks_or_gaps)
    _assert_five_questions(strategy)


def test_senior_production_ai_above_supported_experience(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        posting={
            "raw_text": "Principal AI Engineer. Python required.",
            "title": "Principal AI Engineer",
        },
        seniority={
            "level": "principal",
            "ambiguous": False,
            "evidence": [{"excerpt": "Principal AI Engineer", "section": "title"}],
        },
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong core skills with production tenure gap.",
            [
                _finding(summary="Python aligns."),
                _finding(
                    kind="gap",
                    summary="Required commercial production AI tenure is not established.",
                    job_evidence=[{"source": "seniority"}],
                    profile_evidence=[],
                ),
            ],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercially acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio is strong but not commercial tenure.",
            [
                _finding(
                    summary="Portfolio supports production-minded AI work.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:governance-document-rag",
                        }
                    ],
                )
            ],
        ),
        summary="Senior stretch principal AI role.",
    )
    strategy = _plan(
        assessment,
        _portfolio_match_for(analysis, project_id="governance-document-rag"),
        profile,
    )

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.pursuit_posture != "prioritise"
    assert any("seniority" in risk.summary.casefold() for risk in strategy.risks_or_gaps)
    assert any(
        action.kind == "consider_reviewing_seniority_expectations"
        for action in strategy.next_actions
    )
    assert "ready" not in strategy.summary.casefold() or "not" in strategy.summary.casefold()
    _assert_five_questions(strategy)


def test_outside_target_data_engineer_without_volume(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        posting={
            "raw_text": "Data Engineer. Python and SQL required.",
            "title": "Data Engineer",
        },
        role_family={
            "family": "data_engineering",
            "evidence": [{"excerpt": "Data Engineer", "section": "title"}],
        },
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "moderate",
            "Transferable data engineering skills.",
            [_finding(summary="Python aligns with data engineering work.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercially acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "weak",
            "Portfolio is AI-focused rather than classic DE.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Limited classic data-engineering portfolio emphasis.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:payroll-diagnostics-engine",
                        }
                    ],
                )
            ],
        ),
        summary="Traditional Data Engineer role.",
    )
    strategy = _plan(assessment, _portfolio_match_for(analysis), profile)

    assert strategy.pursuit_posture == "do_not_prioritise"
    assert strategy.application_tier == "bronze"
    assert strategy.effort_level == "none"
    assert "never apply" not in strategy.summary.casefold()
    assert "forbidden" not in strategy.summary.casefold()
    _assert_five_questions(strategy)


def test_low_fit_volume_application(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        posting={
            "raw_text": "Data Engineer. Python required.",
            "title": "Data Engineer",
        },
        role_family={
            "family": "data_engineering",
            "evidence": [{"excerpt": "Data Engineer", "section": "title"}],
        },
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "weak",
            "Weak strategic fit for AI search.",
            [_finding(summary="Only generic Python overlap.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercially acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "weak",
            "Portfolio not optimised for classic DE.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Limited DE portfolio emphasis.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:payroll-diagnostics-engine",
                        }
                    ],
                )
            ],
        ),
        summary="Low-fit volume candidate.",
    )
    strategy = _plan(
        assessment,
        _portfolio_match_for(analysis),
        profile,
        operating_context=SearchOperatingContext(volume_applications_enabled=True),
    )

    assert strategy.pursuit_posture == "low_effort_submit"
    assert strategy.application_tier == "silver"
    assert strategy.effort_level == "minimal"
    assert strategy.practical_value == "volume_obligation"
    assert any(
        action.kind == "consider_low_effort_application"
        for action in strategy.next_actions
    )
    assert strategy.owner_review_required is True
    _assert_five_questions(strategy)


def test_insufficient_information(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(technologies=[], responsibilities=[])
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "unknown",
            "Too little technical evidence.",
            [
                _finding(
                    kind="uncertainty",
                    summary="No usable technologies or responsibilities.",
                    job_evidence=[{"source": "role_family"}],
                    profile_evidence=[],
                )
            ],
        ),
        commercial=_dimension(
            "commercial",
            "unknown",
            "Commercial fit unknown.",
            [
                _finding(
                    kind="uncertainty",
                    summary="Commercial details are sparse.",
                    job_evidence=[{"source": "compensation"}],
                    profile_evidence=[],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "unknown",
            "Portfolio fit unknown.",
            [
                _finding(
                    kind="uncertainty",
                    summary="Cannot assess portfolio against sparse requirements.",
                    job_evidence=[{"source": "role_family"}],
                    profile_evidence=[],
                )
            ],
        ),
        summary="Insufficient information.",
    )
    strategy = _plan(
        assessment,
        _portfolio_match_for(analysis, ranked=False),
        profile,
    )

    assert strategy.pursuit_posture == "insufficient_information"
    assert strategy.insufficient_information is True
    assert strategy.application_tier == "bronze"
    assert strategy.practical_value == "deferred_pending_information"
    assert strategy.manual_checks
    assert any(
        action.kind == "consider_gathering_missing_job_information"
        for action in strategy.next_actions
    )
    _assert_five_questions(strategy)


def test_incompatible_employment_type(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        employment={
            "working_hours": "unspecified",
            "engagement_type": "contract",
            "evidence": [{"excerpt": "12-month contract"}],
        }
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Technically strong.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "mixed",
            "Contract conflicts with full-time preference.",
            [
                _finding(
                    kind="conflict",
                    summary="Contract engagement conflicts with full-time preference.",
                    job_evidence=[{"source": "employment"}],
                    profile_evidence=[
                        {
                            "source": "preference",
                            "ref": "preference:employment_types",
                        }
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Contract role with full-time preference conflict.",
    )
    strategy = _plan(assessment, _portfolio_match_for(analysis), profile)

    assert strategy.decision_blockers
    assert strategy.pursuit_posture == "do_not_prioritise"
    assert strategy.application_tier == "bronze"
    _assert_five_questions(strategy)


def test_location_mismatch_soft_constraint(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        location={
            "clarity": "stated",
            "summary": "Sydney CBD",
            "evidence": [{"excerpt": "Sydney CBD onsite"}],
        },
        work_arrangement={
            "arrangement": "onsite",
            "evidence": [{"excerpt": "Sydney CBD onsite"}],
        },
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Location is a soft commercial concern.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Sydney onsite differs from Melbourne preference.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Location mismatch soft constraint.",
    )
    strategy = _plan(assessment, _portfolio_match_for(analysis), profile)

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.pursuit_posture != "do_not_prioritise"
    assert any(
        action.kind == "consider_reviewing_location_or_arrangement"
        for action in strategy.next_actions
    )


def test_salary_unknown_no_invented_conflict(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    assert profile.preferences.salary_min is None
    analysis = _job_analysis(compensation={"clarity": "unstated"})
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit limited by unstated salary.",
            [
                _finding(
                    kind="uncertainty",
                    summary="Compensation is unstated.",
                    job_evidence=[{"source": "compensation"}],
                    profile_evidence=[],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Salary unknown.",
    )
    strategy = _plan(assessment, _portfolio_match_for(analysis), profile)

    assert strategy.pursuit_posture == "prioritise"
    assert strategy.application_tier == "platinum"
    assert not strategy.decision_blockers
    assert any("salary" in item.casefold() or "compensation" in item.casefold() for item in strategy.assumptions)
    assert any(
        "compensation" in check.summary.casefold() or "salary" in check.summary.casefold()
        for check in strategy.manual_checks
    )


def test_salary_conflict_with_confirmed_minimum(golden_profile_path: Path) -> None:
    profile = _profile_with(
        golden_profile_path,
        salary_min=150000,
        salary_currency="AUD",
    )
    analysis = _job_analysis(
        compensation={
            "clarity": "stated",
            "minimum": 90000,
            "maximum": 110000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "$90,000-$110,000 AUD",
            "evidence": [{"excerpt": "$90,000-$110,000 AUD"}],
        }
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "weak",
            "Salary below confirmed minimum.",
            [
                _finding(
                    kind="conflict",
                    summary="Stated salary is below salary_min.",
                    job_evidence=[{"source": "compensation"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:salary_min"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Salary conflict.",
    )
    strategy = _plan(assessment, _portfolio_match_for(analysis), profile)

    assert strategy.application_tier in {"silver", "bronze"}
    assert strategy.pursuit_posture in {"consider", "do_not_prioritise"}
    assert any(
        action.kind == "consider_reviewing_compensation"
        for action in strategy.next_actions
    )


def test_working_rights_manual_check_not_forced_bronze(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis(
        posting={
            "raw_text": (
                "Senior AI Engineer. Python required. Hybrid Melbourne. "
                "Must have unrestricted Australian working rights."
            ),
            "title": "Senior AI Engineer",
        }
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Working-rights requirement present; eligibility unknown.",
            [
                _finding(
                    kind="uncertainty",
                    summary="Working-rights requirement cannot be confirmed from profile.",
                    job_evidence=[
                        {
                            "source": "employment",
                            "excerpt": "Must have unrestricted Australian working rights",
                        }
                    ],
                    profile_evidence=[],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Working rights check required.",
    )
    strategy = _plan(assessment, _portfolio_match_for(analysis), profile)

    assert strategy.application_tier in {"platinum", "gold"}
    assert any(
        "working" in check.summary.casefold() for check in strategy.manual_checks
    )
    assert any(
        action.kind == "consider_verifying_working_rights"
        for action in strategy.next_actions
    )
    assert any("eligibility" in item.casefold() for item in strategy.assumptions)


def test_weak_portfolio_evidence_still_allows_pursue_or_consider(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis()
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "weak",
            "Portfolio evidence is weak.",
            [
                _finding(
                    kind="gap",
                    summary="Limited portfolio overlap for this role.",
                    job_evidence=[
                        {"source": "technology", "item_index": 0, "name": "Python"}
                    ],
                    profile_evidence=[],
                )
            ],
        ),
        summary="Strong technical, weak portfolio.",
    )
    strategy = _plan(
        assessment,
        _portfolio_match_for(analysis, ranked=False),
        profile,
    )

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.application_tier != "bronze"
    assert strategy.portfolio_emphasis == []
    assert any("portfolio" in risk.summary.casefold() for risk in strategy.risks_or_gaps)


def test_repeated_plan_is_deterministic(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis()
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Determinism check.",
    )
    match = _portfolio_match_for(analysis)
    first = _plan(assessment, match, profile)
    second = _plan(assessment, match, profile)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


class _StaticPayloadPlanner:
    def __init__(self, payload: ApplicationStrategyPayload) -> None:
        self._payload = payload

    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        operating_context: SearchOperatingContext,
    ) -> ApplicationStrategyPayload:
        _ = assessment, portfolio_match, profile, operating_context
        return self._payload


def test_malformed_and_forbidden_payloads_rejected(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis()
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Trust checks.",
    )
    match = _portfolio_match_for(analysis)

    bad_tier = {
        "application_tier": "skip",
        "pursuit_posture": "prioritise",
        "practical_value": "career_priority",
        "effort_level": "full",
        "summary": "Bad tier.",
        "reasons": [
            {
                "kind": "alignment",
                "summary": "x",
                "importance": "material",
                "evidence": [
                    {
                        "origin": "opportunity_assessment",
                        "assessment_dimension": "technical",
                        "assessment_judgment": "strong",
                    }
                ],
            }
        ],
        "next_actions": [
            {
                "kind": "consider_owner_review",
                "summary": "Review.",
                "evidence": [
                    {
                        "origin": "opportunity_assessment",
                        "assessment_dimension": "technical",
                        "assessment_judgment": "strong",
                    }
                ],
            }
        ],
        "owner_review_required": True,
        "insufficient_information": False,
    }
    with pytest.raises(ApplicationStrategyValidationError):
        ApplicationStrategyService(_StaticPayloadPlanner(bad_tier)).plan(
            assessment, match, profile
        )

    embedded = dict(bad_tier)
    embedded["application_tier"] = "platinum"
    embedded["opportunity_assessment"] = {"embedded": True}
    with pytest.raises(ApplicationStrategyValidationError):
        ApplicationStrategyService(_StaticPayloadPlanner(embedded)).plan(
            assessment, match, profile
        )

    bad_ref = dict(bad_tier)
    bad_ref["application_tier"] = "platinum"
    bad_ref["reasons"] = [
        {
            "kind": "alignment",
            "summary": "Bad judgment citation.",
            "importance": "material",
            "evidence": [
                {
                    "origin": "opportunity_assessment",
                    "assessment_dimension": "technical",
                    "assessment_judgment": "misaligned",
                }
            ],
        }
    ]
    with pytest.raises(ApplicationStrategyValidationError):
        ApplicationStrategyService(_StaticPayloadPlanner(bad_ref)).plan(
            assessment, match, profile
        )


def test_posting_identity_mismatch_rejected(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis()
    other = _job_analysis(
        posting={
            "raw_text": "Different posting text entirely.",
            "title": "Senior AI Engineer",
            "company": "Example AI Co",
        }
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Mismatch check.",
    )
    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        _plan(assessment, _portfolio_match_for(other), profile)
    assert "same JobPosting identity" in exc_info.value.errors[0].msg


def test_planner_errors_propagate(golden_profile_path: Path) -> None:
    class _FailingPlanner:
        def plan(self, assessment, portfolio_match, profile, operating_context):
            _ = assessment, portfolio_match, profile, operating_context
            raise ApplicationStrategyError("planner failed")

    profile = _golden_profile(golden_profile_path)
    analysis = _job_analysis()
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Strong technical fit.",
            [_finding(summary="Python aligns.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit acceptable.",
            [
                _finding(
                    summary="Location aligns.",
                    job_evidence=[{"source": "location"}],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio supports the role.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Failure propagation.",
    )
    with pytest.raises(ApplicationStrategyError, match="planner failed"):
        ApplicationStrategyService(_FailingPlanner()).plan(
            assessment,
            _portfolio_match_for(analysis),
            profile,
        )
