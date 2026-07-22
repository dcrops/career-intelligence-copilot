"""Phase B policy tests for DeterministicStrategyPlanner."""

from __future__ import annotations

from typing import Any

import pytest
from career_intelligence.application_strategy import (
    ApplicationStrategy,
    ApplicationStrategyService,
    SearchOperatingContext,
)
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile

from .helpers import (
    job_analysis,
    minimal_profile,
    portfolio_match,
    portfolio_match_payload,
)

_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "cover_letter_body",
        "cv_body",
        "outreach",
        "submit_application",
        "interview_probability",
        "percentage",
        "score",
        "apply_decision",
    }
)


def _service() -> ApplicationStrategyService:
    return ApplicationStrategyService(DeterministicStrategyPlanner())


def _profile_with(**preference_updates: Any) -> CareerProfile:
    profile = minimal_profile()
    preferences = profile.preferences.model_copy(update=preference_updates)
    return profile.model_copy(update={"preferences": preferences})


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


def _plan(
    assessment: OpportunityAssessment,
    match: PortfolioMatch,
    profile: CareerProfile | None = None,
    *,
    operating_context: SearchOperatingContext | None = None,
) -> ApplicationStrategy:
    return _service().plan(
        assessment,
        match,
        profile or minimal_profile(),
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


def _strong_ai_analysis(**overrides: object) -> JobAnalysis:
    return job_analysis(**overrides)


def test_strong_ai_engineer_opportunity_prioritises_platinum() -> None:
    analysis = _strong_ai_analysis(
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
                    summary="Example project supports AI engineering narrative.",
                    profile_evidence=[
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Strong AI Engineer opportunity.",
    )
    match = portfolio_match(analysis)
    strategy = _plan(assessment, match)

    assert strategy.pursuit_posture == "prioritise"
    assert strategy.application_tier == "platinum"
    assert strategy.effort_level == "full"
    assert strategy.practical_value == "career_priority"
    assert strategy.portfolio_emphasis
    assert strategy.portfolio_emphasis[0].project_id == "example-project"
    assert any(
        action.kind == "consider_cv_tailoring" for action in strategy.next_actions
    )
    assert strategy.owner_review_required is True


def test_applied_ai_mixed_commercial_is_pursue_or_consider() -> None:
    analysis = job_analysis(
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Applied AI with mixed commercial fit.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.application_tier in {"gold", "silver"}
    assert strategy.effort_level in {"targeted", "minimal"}
    assert any("commercial" in risk.summary.casefold() for risk in strategy.risks_or_gaps)


def test_senior_production_ai_above_evidence_reduces_posture() -> None:
    analysis = job_analysis(
        posting={
            "raw_text": "Principal AI Engineer. Python required. Production LLM tenure.",
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
            "Strong core skills but production tenure gap.",
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Senior stretch principal AI role.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.application_tier in {"gold", "silver"}
    assert strategy.pursuit_posture != "prioritise"
    assert any("seniority" in risk.summary.casefold() for risk in strategy.risks_or_gaps)
    assert any(
        action.kind == "consider_reviewing_seniority_expectations"
        for action in strategy.next_actions
    )


def test_outside_scope_data_engineer_is_bronze_without_volume() -> None:
    analysis = job_analysis(
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Traditional Data Engineer role.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.pursuit_posture == "do_not_prioritise"
    assert strategy.application_tier == "bronze"
    assert strategy.effort_level == "none"
    assert "never apply" not in strategy.summary.casefold()
    assert any(
        action.kind == "consider_logging_and_deprioritising"
        for action in strategy.next_actions
    )


def test_insufficient_information_posture() -> None:
    analysis = job_analysis(
        technologies=[],
        responsibilities=[],
    )
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
    match = PortfolioMatch.model_validate(
        portfolio_match_payload(
            analysis,
            ranked_projects=[],
            unranked_project_ids=["example-project"],
            summary="Insufficient evidence to rank projects.",
            insufficient_evidence=True,
        )
    )
    strategy = _plan(assessment, match)

    assert strategy.pursuit_posture == "insufficient_information"
    assert strategy.insufficient_information is True
    assert strategy.application_tier == "bronze"
    assert strategy.practical_value == "deferred_pending_information"
    assert any(
        action.kind == "consider_gathering_missing_job_information"
        for action in strategy.next_actions
    )
    assert strategy.manual_checks


def test_incompatible_employment_type_is_blocker() -> None:
    analysis = job_analysis(
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Contract role with full-time preference conflict.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.decision_blockers
    assert strategy.pursuit_posture == "do_not_prioritise"
    assert strategy.application_tier == "bronze"


def test_location_mismatch_reduces_but_does_not_auto_reject() -> None:
    analysis = job_analysis(
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Location mismatch soft constraint.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.application_tier in {"gold", "silver"}
    assert strategy.pursuit_posture != "do_not_prioritise"
    assert any(
        action.kind == "consider_reviewing_location_or_arrangement"
        for action in strategy.next_actions
    )


def test_salary_conflict_reduces_tier() -> None:
    analysis = job_analysis(
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
    profile = _profile_with(salary_min=150000, salary_currency="AUD")
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Salary conflict.",
    )
    strategy = _plan(assessment, portfolio_match(analysis), profile)

    assert strategy.application_tier in {"silver", "bronze"}
    assert strategy.pursuit_posture in {"consider", "do_not_prioritise"}
    assert any("salary" in risk.summary.casefold() or "compensation" in risk.summary.casefold() for risk in strategy.risks_or_gaps)
    assert any(
        action.kind == "consider_reviewing_compensation"
        for action in strategy.next_actions
    )


def test_salary_unknown_does_not_invent_conflict() -> None:
    analysis = job_analysis(compensation={"clarity": "unstated"})
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
                ),
                _finding(
                    kind="assumption",
                    summary="salary_min is unset.",
                    assumption="No salary minimum is configured.",
                    job_evidence=[],
                    profile_evidence=[
                        {"source": "preference", "ref": "preference:salary_min"}
                    ],
                ),
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Salary unknown.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.pursuit_posture == "prioritise"
    assert strategy.application_tier == "platinum"
    assert not any("below" in item.casefold() for item in strategy.decision_blockers)
    assert any("compensation" in item.casefold() or "salary" in item.casefold() for item in strategy.assumptions)
    assert any(
        check.summary.casefold().find("compensation") >= 0
        or check.summary.casefold().find("salary") >= 0
        for check in strategy.manual_checks
    )


def test_working_rights_manual_check_without_forced_bronze() -> None:
    analysis = job_analysis(
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Working rights check required.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.application_tier in {"platinum", "gold"}
    assert any(
        "working-rights" in check.summary.casefold()
        or "working rights" in check.summary.casefold()
        for check in strategy.manual_checks
    )
    assert any(
        action.kind == "consider_verifying_working_rights"
        for action in strategy.next_actions
    )
    assert any("eligibility" in item.casefold() for item in strategy.assumptions)


def test_weak_portfolio_does_not_force_bronze() -> None:
    analysis = job_analysis()
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
    match = PortfolioMatch.model_validate(
        portfolio_match_payload(
            analysis,
            ranked_projects=[],
            unranked_project_ids=["example-project"],
            summary="Insufficient evidence to rank projects.",
            insufficient_evidence=True,
        )
    )
    strategy = _plan(assessment, match)

    assert strategy.pursuit_posture in {"pursue", "consider"}
    assert strategy.application_tier in {"gold", "silver"}
    assert strategy.application_tier != "bronze"
    assert strategy.portfolio_emphasis == []
    assert any("portfolio" in risk.summary.casefold() for risk in strategy.risks_or_gaps)


def test_low_effort_volume_application() -> None:
    analysis = job_analysis(
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Low-fit volume candidate.",
    )
    strategy = _plan(
        assessment,
        portfolio_match(analysis),
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


def test_repeated_deterministic_output() -> None:
    analysis = job_analysis()
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Determinism check.",
    )
    match = portfolio_match(analysis)
    first = _plan(assessment, match)
    second = _plan(assessment, match)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_reasons_are_evidence_backed_and_next_actions_advisory() -> None:
    analysis = job_analysis()
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Evidence and next-action checks.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert strategy.reasons
    assert all(reason.evidence for reason in strategy.reasons)
    assert strategy.next_actions
    assert all(action.kind.startswith("consider_") for action in strategy.next_actions)
    assert len(strategy.next_actions) <= 5
    assert any(action.kind == "consider_owner_review" for action in strategy.next_actions)


def test_no_forbidden_execution_or_score_fields() -> None:
    analysis = job_analysis()
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
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Forbidden field scan.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))
    names = _collect_field_names(strategy.model_dump(mode="json"))
    assert names.isdisjoint(_FORBIDDEN_FIELD_NAMES)


def test_planner_not_publicly_exported() -> None:
    import career_intelligence.application_strategy as api

    assert "DeterministicStrategyPlanner" not in api.__all__
    assert "DeterministicStrategyPlanner" not in dir(api)
