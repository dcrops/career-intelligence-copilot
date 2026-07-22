"""Phase C fixture-planner and fixture-composition tests for FR-005."""

from __future__ import annotations

from pathlib import Path

import career_intelligence.application_strategy as strategy_api
import pytest
from career_intelligence.application_strategy import (
    ApplicationStrategy,
    ApplicationStrategyError,
    ApplicationStrategyService,
    ApplicationStrategyValidationError,
    SearchOperatingContext,
)
from career_intelligence.application_strategy.fixture_planner import FixtureStrategyPlanner
from career_intelligence.application_strategy.fixtures import (
    MARKER_STRATEGY_SALARY_CONFLICT,
    MARKER_STRATEGY_VOLUME,
    MARKER_STRATEGY_WEAK_PORTFOLIO,
    STRATEGY_FIXTURE_BUILDERS,
    posting_strategy_salary_conflict,
    posting_strategy_volume,
    posting_strategy_weak_portfolio,
    strategy_salary_conflict,
    strategy_strong_applied_ai,
    strategy_volume_low_fit,
    strategy_weak_portfolio,
)
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_AMBIGUOUS_SENIORITY,
    MARKER_APPLIED_AI,
    MARKER_CONTRACT,
    MARKER_DATA_ENGINEER,
    MARKER_MISSING_SALARY,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
    posting_ai_engineer,
    posting_ambiguous_seniority,
    posting_applied_ai_engineer,
    posting_contract,
    posting_data_engineer,
    posting_missing_salary,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment import OpportunityAssessmentService
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching import PortfolioMatchingService
from career_intelligence.portfolio_matching.fixture_matcher import FixtureMatcher
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile import CareerProfile, CareerProfileService

_GOLDEN_PROJECT_IDS = [
    "operational-intelligence-copilot",
    "governance-document-rag",
    "payroll-diagnostics-engine",
    "public-holiday-entitlements",
]

_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "job_analysis",
        "profile",
        "career_profile",
        "opportunity_assessment",
        "portfolio_match",
        "operating_context",
        "search_operating_context",
    }
)


def _golden_profile() -> CareerProfile:
    path = Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"
    return CareerProfileService.from_path(path).load()


def _job_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def _assessment_service() -> OpportunityAssessmentService:
    return OpportunityAssessmentService(FixtureAssessor())


def _match_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(FixtureMatcher())


def _strategy_service() -> ApplicationStrategyService:
    return ApplicationStrategyService(FixtureStrategyPlanner())


def _cover_all_projects(match_payload: dict[str, object] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "ranked_projects": [],
        "unranked_project_ids": list(_GOLDEN_PROJECT_IDS),
        "summary": "Fixture portfolio coverage for strategy contract tests.",
        "insufficient_evidence": True,
    }
    if match_payload is not None:
        payload.update(match_payload)
    return payload


def _portfolio_match_for(
    analysis: JobAnalysis,
    payload: dict[str, object] | None = None,
) -> PortfolioMatch:
    body = _cover_all_projects(payload)
    body["job_analysis"] = analysis.model_dump(mode="json")
    return PortfolioMatch.model_validate(body)


def _chain_shared_marker(posting_builder: object) -> ApplicationStrategy:
    profile = _golden_profile()
    analysis = _job_service().analyse(posting_builder())  # type: ignore[operator]
    assessment = _assessment_service().assess(analysis, profile)
    match = _match_service().match(analysis, profile)
    return _strategy_service().plan(assessment, match, profile)


def test_all_strategy_fixture_builders_return_serialisable_payloads() -> None:
    for marker, builder in STRATEGY_FIXTURE_BUILDERS.items():
        payload = builder()
        assert isinstance(payload, dict)
        assert marker
        for key in _FORBIDDEN_PAYLOAD_KEYS:
            assert key not in payload
        assert payload["owner_review_required"] is True
        assert "application_tier" in payload
        assert "pursuit_posture" in payload
        assert "next_actions" in payload
        assert len(payload["next_actions"]) <= 5
        assert all(
            str(action["kind"]).startswith("consider_")
            for action in payload["next_actions"]  # type: ignore[index]
        )


def test_fixture_planner_requires_recognised_marker() -> None:
    analysis = JobAnalysis.model_validate(
        {
            "posting": {
                "raw_text": "No fixture marker here.",
                "title": "Unknown Role",
            },
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "location": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
            "employment": {},
            "experience_requirements": [],
        }
    )
    assessment = OpportunityAssessment.model_validate(
        {
            "job_analysis": analysis.model_dump(mode="json"),
            "technical_fit": {
                "dimension": "technical",
                "judgment": "unknown",
                "summary": "Unknown.",
                "findings": [
                    {
                        "kind": "uncertainty",
                        "summary": "Unknown technical fit.",
                        "importance": "material",
                        "job_evidence": [{"source": "role_family"}],
                        "profile_evidence": [],
                    }
                ],
            },
            "commercial_fit": {
                "dimension": "commercial",
                "judgment": "unknown",
                "summary": "Unknown.",
                "findings": [
                    {
                        "kind": "uncertainty",
                        "summary": "Unknown commercial fit.",
                        "importance": "material",
                        "job_evidence": [{"source": "compensation"}],
                        "profile_evidence": [],
                    }
                ],
            },
            "portfolio_fit": {
                "dimension": "portfolio",
                "judgment": "unknown",
                "summary": "Unknown.",
                "findings": [
                    {
                        "kind": "uncertainty",
                        "summary": "Unknown portfolio fit.",
                        "importance": "material",
                        "job_evidence": [{"source": "role_family"}],
                        "profile_evidence": [],
                    }
                ],
            },
            "summary": {"summary": "Unknown.", "key_alignments": [], "key_gaps": []},
        }
    )
    planner = FixtureStrategyPlanner()
    with pytest.raises(ApplicationStrategyError, match="No fixture application strategy"):
        planner.plan(
            assessment,
            _portfolio_match_for(analysis),
            _golden_profile(),
            SearchOperatingContext(),
        )


def test_service_composition_strong_applied_ai() -> None:
    strategy = _chain_shared_marker(posting_applied_ai_engineer)

    assert strategy.pursuit_posture == "prioritise"
    assert strategy.application_tier == "platinum"
    assert strategy.effort_level == "full"
    assert strategy.owner_review_required is True
    assert strategy.portfolio_emphasis
    assert strategy.portfolio_emphasis[0].project_id == "operational-intelligence-copilot"
    assert MARKER_APPLIED_AI in strategy.job_analysis.posting.raw_text


def test_service_composition_ai_engineer_seniority_stretch() -> None:
    strategy = _chain_shared_marker(posting_ai_engineer)

    assert strategy.pursuit_posture == "pursue"
    assert strategy.application_tier == "gold"
    assert strategy.portfolio_emphasis
    assert strategy.portfolio_emphasis[0].project_id == "governance-document-rag"
    assert any(
        action.kind == "consider_reviewing_seniority_expectations"
        for action in strategy.next_actions
    )
    assert MARKER_AI_ENGINEER in strategy.job_analysis.posting.raw_text


def test_service_composition_data_engineer_bronze() -> None:
    strategy = _chain_shared_marker(posting_data_engineer)

    assert strategy.pursuit_posture == "do_not_prioritise"
    assert strategy.application_tier == "bronze"
    assert strategy.effort_level == "none"
    assert "never apply" not in strategy.summary.casefold()
    assert MARKER_DATA_ENGINEER in strategy.job_analysis.posting.raw_text


def test_service_composition_working_rights_insufficient() -> None:
    strategy = _chain_shared_marker(posting_working_rights)

    assert strategy.pursuit_posture == "insufficient_information"
    assert strategy.insufficient_information is True
    assert strategy.portfolio_emphasis == []
    assert any(
        action.kind == "consider_verifying_working_rights"
        for action in strategy.next_actions
    )
    assert MARKER_WORKING_RIGHTS in strategy.job_analysis.posting.raw_text


def test_service_composition_no_technologies_portfolio_emphasis_present() -> None:
    strategy = _chain_shared_marker(posting_no_technologies)

    assert strategy.pursuit_posture == "consider"
    assert strategy.application_tier == "silver"
    assert strategy.portfolio_emphasis
    assert strategy.portfolio_emphasis[0].project_id == "operational-intelligence-copilot"
    assert MARKER_NO_TECHNOLOGIES in strategy.job_analysis.posting.raw_text


def test_volume_context_overrides_data_engineer_fixture() -> None:
    profile = _golden_profile()
    analysis = _job_service().analyse(posting_data_engineer())
    assessment = _assessment_service().assess(analysis, profile)
    match = _match_service().match(analysis, profile)

    strategy = _strategy_service().plan(
        assessment,
        match,
        profile,
        operating_context=SearchOperatingContext(volume_applications_enabled=True),
    )

    assert strategy.pursuit_posture == "low_effort_submit"
    assert strategy.application_tier == "silver"
    assert strategy.practical_value == "volume_obligation"
    assert any(
        action.kind == "consider_low_effort_application"
        for action in strategy.next_actions
    )


def test_volume_context_with_strategy_volume_marker() -> None:
    profile = _golden_profile()
    analysis = JobAnalysis.model_validate(
        {
            "posting": posting_strategy_volume().model_dump(mode="json"),
            "role_family": {
                "family": "data_engineering",
                "evidence": [{"excerpt": "Data Engineer"}],
            },
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [
                {
                    "name": "Python",
                    "level": "required",
                    "evidence": [{"excerpt": "Python required"}],
                }
            ],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "location": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
            "employment": {},
            "experience_requirements": [],
        }
    )
    # Judgments must match the volume fixture evidence citations.
    assessment = OpportunityAssessment.model_validate(
        {
            "job_analysis": analysis.model_dump(mode="json"),
            "technical_fit": {
                "dimension": "technical",
                "judgment": "mixed",
                "summary": "Mixed technical fit.",
                "findings": [
                    {
                        "kind": "alignment",
                        "summary": "Python aligns.",
                        "importance": "material",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "Python",
                            }
                        ],
                        "profile_evidence": [
                            {"source": "skill", "ref": "skill:Python"}
                        ],
                    }
                ],
            },
            "commercial_fit": {
                "dimension": "commercial",
                "judgment": "moderate",
                "summary": "Moderate commercial fit.",
                "findings": [
                    {
                        "kind": "uncertainty",
                        "summary": "Compensation unstated.",
                        "importance": "minor",
                        "job_evidence": [{"source": "compensation"}],
                        "profile_evidence": [],
                    }
                ],
            },
            "portfolio_fit": {
                "dimension": "portfolio",
                "judgment": "weak",
                "summary": "Weak portfolio fit.",
                "findings": [
                    {
                        "kind": "gap",
                        "summary": "Limited portfolio overlap.",
                        "importance": "material",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "Python",
                            }
                        ],
                        "profile_evidence": [],
                    }
                ],
            },
            "summary": {"summary": "Volume scenario.", "key_alignments": [], "key_gaps": []},
        }
    )
    strategy = _strategy_service().plan(
        assessment,
        _portfolio_match_for(analysis),
        profile,
        operating_context=SearchOperatingContext(volume_applications_enabled=True),
    )

    assert MARKER_STRATEGY_VOLUME in strategy.job_analysis.posting.raw_text
    assert strategy.pursuit_posture == "low_effort_submit"
    assert strategy.model_dump(mode="json") == _strategy_service().plan(
        assessment,
        _portfolio_match_for(analysis),
        profile,
        operating_context=SearchOperatingContext(volume_applications_enabled=True),
    ).model_dump(mode="json")


def test_missing_salary_and_contract_via_assessor_and_manual_match() -> None:
    profile = _golden_profile()

    salary_analysis = _job_service().analyse(posting_missing_salary())
    salary_assessment = _assessment_service().assess(salary_analysis, profile)
    salary_strategy = _strategy_service().plan(
        salary_assessment,
        _portfolio_match_for(salary_analysis),
        profile,
    )
    assert MARKER_MISSING_SALARY in salary_strategy.job_analysis.posting.raw_text
    assert salary_strategy.pursuit_posture == "pursue"
    assert any(
        action.kind == "consider_reviewing_compensation"
        for action in salary_strategy.next_actions
    )

    contract_analysis = _job_service().analyse(posting_contract())
    contract_assessment = _assessment_service().assess(contract_analysis, profile)
    contract_strategy = _strategy_service().plan(
        contract_assessment,
        _portfolio_match_for(contract_analysis),
        profile,
    )
    assert MARKER_CONTRACT in contract_strategy.job_analysis.posting.raw_text
    assert contract_strategy.pursuit_posture == "do_not_prioritise"
    assert contract_strategy.decision_blockers
    assert any(
        action.kind == "consider_reviewing_location_or_arrangement"
        for action in contract_strategy.next_actions
    )


def test_ambiguous_seniority_fixture_composition() -> None:
    profile = _golden_profile()
    analysis = _job_service().analyse(posting_ambiguous_seniority())
    assessment = _assessment_service().assess(analysis, profile)
    strategy = _strategy_service().plan(
        assessment,
        _portfolio_match_for(analysis),
        profile,
    )

    assert MARKER_AMBIGUOUS_SENIORITY in strategy.job_analysis.posting.raw_text
    assert strategy.pursuit_posture == "consider"
    assert any(
        action.kind == "consider_reviewing_seniority_expectations"
        for action in strategy.next_actions
    )


def test_strategy_only_weak_portfolio_and_salary_conflict() -> None:
    profile = _golden_profile()

    weak_analysis = JobAnalysis.model_validate(
        {
            "posting": posting_strategy_weak_portfolio().model_dump(mode="json"),
            "role_family": {
                "family": "ai_engineering",
                "evidence": [{"excerpt": "AI Engineer"}],
            },
            "seniority": {"level": "mid", "ambiguous": False, "evidence": [{"excerpt": "AI Engineer"}]},
            "technologies": [
                {
                    "name": "Python",
                    "level": "required",
                    "evidence": [{"excerpt": "Python required"}],
                }
            ],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "location": {
                "clarity": "stated",
                "summary": "Melbourne",
                "evidence": [{"excerpt": "Hybrid Melbourne"}],
            },
            "work_arrangement": {
                "arrangement": "hybrid",
                "evidence": [{"excerpt": "Hybrid Melbourne"}],
            },
            "employment": {},
            "experience_requirements": [],
        }
    )
    weak_assessment = OpportunityAssessment.model_validate(
        {
            "job_analysis": weak_analysis.model_dump(mode="json"),
            "technical_fit": {
                "dimension": "technical",
                "judgment": "strong",
                "summary": "Strong technical fit.",
                "findings": [
                    {
                        "kind": "alignment",
                        "summary": "Python aligns.",
                        "importance": "material",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "Python",
                            }
                        ],
                        "profile_evidence": [
                            {"source": "skill", "ref": "skill:Python"}
                        ],
                    }
                ],
            },
            "commercial_fit": {
                "dimension": "commercial",
                "judgment": "moderate",
                "summary": "Moderate commercial fit.",
                "findings": [
                    {
                        "kind": "alignment",
                        "summary": "Location aligns.",
                        "importance": "material",
                        "job_evidence": [{"source": "location"}],
                        "profile_evidence": [
                            {
                                "source": "preference",
                                "ref": "preference:locations",
                            }
                        ],
                    }
                ],
            },
            "portfolio_fit": {
                "dimension": "portfolio",
                "judgment": "weak",
                "summary": "Weak portfolio fit.",
                "findings": [
                    {
                        "kind": "gap",
                        "summary": "Limited portfolio overlap.",
                        "importance": "material",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "Python",
                            }
                        ],
                        "profile_evidence": [],
                    }
                ],
            },
            "summary": {
                "summary": "Weak portfolio scenario.",
                "key_alignments": [],
                "key_gaps": [],
            },
        }
    )
    weak_strategy = _strategy_service().plan(
        weak_assessment,
        _portfolio_match_for(weak_analysis),
        profile,
    )
    assert MARKER_STRATEGY_WEAK_PORTFOLIO in weak_strategy.job_analysis.posting.raw_text
    assert weak_strategy.pursuit_posture == "pursue"
    assert weak_strategy.portfolio_emphasis == []

    salary_analysis = JobAnalysis.model_validate(
        {
            "posting": posting_strategy_salary_conflict().model_dump(mode="json"),
            "role_family": {
                "family": "ai_engineering",
                "evidence": [{"excerpt": "AI Engineer"}],
            },
            "seniority": {"level": "mid", "ambiguous": False, "evidence": [{"excerpt": "AI Engineer"}]},
            "technologies": [
                {
                    "name": "Python",
                    "level": "required",
                    "evidence": [{"excerpt": "Python required"}],
                }
            ],
            "responsibilities": [],
            "compensation": {
                "clarity": "stated",
                "minimum": 90000,
                "maximum": 110000,
                "currency": "AUD",
                "period": "year",
                "raw_text": "$90,000-$110,000 AUD",
                "evidence": [{"excerpt": "$90,000-$110,000 AUD"}],
            },
            "location": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
            "employment": {},
            "experience_requirements": [],
        }
    )
    salary_assessment = OpportunityAssessment.model_validate(
        {
            "job_analysis": salary_analysis.model_dump(mode="json"),
            "technical_fit": {
                "dimension": "technical",
                "judgment": "strong",
                "summary": "Strong technical fit.",
                "findings": [
                    {
                        "kind": "alignment",
                        "summary": "Python aligns.",
                        "importance": "material",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "Python",
                            }
                        ],
                        "profile_evidence": [
                            {"source": "skill", "ref": "skill:Python"}
                        ],
                    }
                ],
            },
            "commercial_fit": {
                "dimension": "commercial",
                "judgment": "weak",
                "summary": "Salary conflict.",
                "findings": [
                    {
                        "kind": "conflict",
                        "summary": "Salary below minimum.",
                        "importance": "material",
                        "job_evidence": [{"source": "compensation"}],
                        "profile_evidence": [
                            {
                                "source": "preference",
                                "ref": "preference:salary_min",
                            }
                        ],
                    }
                ],
            },
            "portfolio_fit": {
                "dimension": "portfolio",
                "judgment": "moderate",
                "summary": "Moderate portfolio fit.",
                "findings": [
                    {
                        "kind": "partial_alignment",
                        "summary": "Some project overlap.",
                        "importance": "minor",
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
                                "ref": "project:operational-intelligence-copilot",
                            }
                        ],
                    }
                ],
            },
            "summary": {
                "summary": "Salary conflict scenario.",
                "key_alignments": [],
                "key_gaps": [],
            },
        }
    )
    profile_with_min = profile.model_copy(
        update={
            "preferences": profile.preferences.model_copy(
                update={"salary_min": 150000, "salary_currency": "AUD"}
            )
        }
    )
    salary_strategy = _strategy_service().plan(
        salary_assessment,
        _portfolio_match_for(salary_analysis),
        profile_with_min,
    )
    assert MARKER_STRATEGY_SALARY_CONFLICT in salary_strategy.job_analysis.posting.raw_text
    assert salary_strategy.pursuit_posture == "consider"
    assert any(
        action.kind == "consider_reviewing_compensation"
        for action in salary_strategy.next_actions
    )


def test_mismatched_posting_identity_still_rejected() -> None:
    profile = _golden_profile()
    analysis = _job_service().analyse(posting_applied_ai_engineer())
    assessment = _assessment_service().assess(analysis, profile)
    other = _job_service().analyse(posting_ai_engineer())
    match = _match_service().match(other, profile)

    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        _strategy_service().plan(assessment, match, profile)
    assert "same JobPosting identity" in exc_info.value.errors[0].msg


def test_invalid_fixture_payload_rejected_by_service() -> None:
    class _BrokenFixturePlanner:
        def plan(self, assessment, portfolio_match, profile, operating_context):
            _ = assessment, portfolio_match, profile, operating_context
            payload = dict(strategy_strong_applied_ai())
            payload["application_tier"] = "skip"
            return payload

    profile = _golden_profile()
    analysis = _job_service().analyse(posting_applied_ai_engineer())
    assessment = _assessment_service().assess(analysis, profile)
    match = _match_service().match(analysis, profile)
    service = ApplicationStrategyService(_BrokenFixturePlanner())

    with pytest.raises(ApplicationStrategyValidationError):
        service.plan(assessment, match, profile)


def test_deterministic_fixture_outputs_are_stable() -> None:
    first = strategy_strong_applied_ai()
    second = strategy_strong_applied_ai()
    assert first == second
    assert strategy_volume_low_fit() == strategy_volume_low_fit()
    assert strategy_weak_portfolio() == strategy_weak_portfolio()
    assert strategy_salary_conflict() == strategy_salary_conflict()


def test_fixture_planner_not_publicly_exported() -> None:
    assert "FixtureStrategyPlanner" not in strategy_api.__all__
    assert "FixtureStrategyPlanner" not in dir(strategy_api)
    assert "DeterministicStrategyPlanner" not in dir(strategy_api)
