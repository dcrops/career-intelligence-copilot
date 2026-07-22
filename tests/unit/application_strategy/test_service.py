"""Unit tests for ApplicationStrategyService trust-boundary behaviour."""

from __future__ import annotations

import career_intelligence.application_strategy as strategy_api
import pytest
from career_intelligence.application_strategy import (
    ApplicationStrategy,
    ApplicationStrategyError,
    ApplicationStrategyService,
    ApplicationStrategyValidationError,
    SearchOperatingContext,
)
from career_intelligence.application_strategy.planner import ApplicationStrategyPayload
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile

from .helpers import (
    job_analysis,
    minimal_profile,
    opportunity_assessment,
    portfolio_match,
    valid_strategy_payload,
)


class _StaticPayloadPlanner:
    def __init__(self, payload: ApplicationStrategyPayload) -> None:
        self._payload = payload
        self.received_context: SearchOperatingContext | None = None

    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        operating_context: SearchOperatingContext,
    ) -> ApplicationStrategyPayload:
        _ = assessment, portfolio_match, profile
        self.received_context = operating_context
        return self._payload


class _FailingPlanner:
    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        operating_context: SearchOperatingContext,
    ) -> ApplicationStrategyPayload:
        _ = assessment, portfolio_match, profile, operating_context
        raise ApplicationStrategyError("planner failed")


def test_service_requires_a_planner() -> None:
    with pytest.raises(TypeError):
        ApplicationStrategyService()  # type: ignore[call-arg]


def test_valid_payload_becomes_trusted_application_strategy() -> None:
    analysis = job_analysis()
    assessment = opportunity_assessment(analysis)
    match = portfolio_match(analysis)
    profile = minimal_profile()
    service = ApplicationStrategyService(
        _StaticPayloadPlanner(valid_strategy_payload())
    )

    strategy = service.plan(assessment, match, profile)

    assert isinstance(strategy, ApplicationStrategy)
    assert strategy.job_analysis.posting.title == "Senior AI Engineer"
    assert strategy.application_tier == "platinum"
    assert strategy.owner_review_required is True


def test_default_operating_context_disables_volume_mode() -> None:
    analysis = job_analysis()
    planner = _StaticPayloadPlanner(valid_strategy_payload())
    service = ApplicationStrategyService(planner)

    service.plan(
        opportunity_assessment(analysis),
        portfolio_match(analysis),
        minimal_profile(),
    )

    assert planner.received_context is not None
    assert planner.received_context.volume_applications_enabled is False


def test_explicit_operating_context_is_passed_through() -> None:
    analysis = job_analysis()
    planner = _StaticPayloadPlanner(valid_strategy_payload())
    service = ApplicationStrategyService(planner)
    context = SearchOperatingContext(volume_applications_enabled=True)

    service.plan(
        opportunity_assessment(analysis),
        portfolio_match(analysis),
        minimal_profile(),
        operating_context=context,
    )

    assert planner.received_context is context


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "job_analysis",
        "profile",
        "career_profile",
        "opportunity_assessment",
        "portfolio_match",
        "operating_context",
        "search_operating_context",
    ],
)
def test_forbidden_embedded_inputs_rejected(forbidden_key: str) -> None:
    analysis = job_analysis()
    payload = valid_strategy_payload()
    payload[forbidden_key] = {"embedded": True}
    service = ApplicationStrategyService(_StaticPayloadPlanner(payload))

    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        service.plan(
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )

    assert any(error.loc == (forbidden_key,) for error in exc_info.value.errors)


def test_mismatched_postings_rejected() -> None:
    analysis = job_analysis()
    other = job_analysis(
        posting={
            "raw_text": "Different posting text entirely.",
            "title": "Senior AI Engineer",
            "company": "Example AI Co",
        }
    )
    service = ApplicationStrategyService(
        _StaticPayloadPlanner(valid_strategy_payload())
    )

    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        service.plan(
            opportunity_assessment(analysis),
            portfolio_match(other),
            minimal_profile(),
        )

    assert "same JobPosting identity" in exc_info.value.errors[0].msg


def test_invalid_payload_schema_rejected() -> None:
    analysis = job_analysis()
    payload = valid_strategy_payload()
    payload["application_tier"] = "skip"
    service = ApplicationStrategyService(_StaticPayloadPlanner(payload))

    with pytest.raises(ApplicationStrategyValidationError):
        service.plan(
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )


def test_invalid_evidence_refs_rejected_by_service() -> None:
    analysis = job_analysis()
    payload = valid_strategy_payload(
        reasons=[
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
    )
    service = ApplicationStrategyService(_StaticPayloadPlanner(payload))

    with pytest.raises(ApplicationStrategyValidationError):
        service.plan(
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )


def test_planner_errors_propagate() -> None:
    analysis = job_analysis()
    service = ApplicationStrategyService(_FailingPlanner())

    with pytest.raises(ApplicationStrategyError, match="planner failed"):
        service.plan(
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )


def test_public_exports_do_not_include_planner_implementations() -> None:
    exported = set(strategy_api.__all__)
    assert "ApplicationStrategyService" in exported
    assert "SearchOperatingContext" in exported
    assert "StrategyPlanner" not in exported
    assert "DeterministicStrategyPlanner" not in dir(strategy_api)
    assert "FixtureStrategyPlanner" not in dir(strategy_api)
