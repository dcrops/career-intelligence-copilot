"""Location normalisation and role-family wording regression tests for FR-005."""

from __future__ import annotations

from typing import Any

from career_intelligence.application_strategy import ApplicationStrategyService
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
    _locations_compatible,
    _normalize_location_tokens,
    _role_family_reason_phrase,
)
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import posting_junior_software_devops
from career_intelligence.portfolio_matching import PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.profile import CareerProfileService

from .helpers import (
    fixtures_dir,
    job_analysis,
    minimal_profile,
    portfolio_match,
)


def _finding(
    *,
    kind: str = "alignment",
    summary: str,
    importance: str = "material",
    job_evidence: list[dict[str, Any]] | None = None,
    profile_evidence: list[dict[str, Any]] | None = None,
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
    if kind == "gap":
        payload["profile_evidence"] = profile_evidence or []
    return payload


def _dimension(
    name: str,
    judgment: str,
    summary: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "dimension": name,
        "judgment": judgment,
        "summary": summary,
        "findings": findings,
    }


def _assessment_for(analysis, *, technical, commercial, portfolio, summary: str):
    from career_intelligence.opportunity_assessment.models import OpportunityAssessment

    return OpportunityAssessment.model_validate(
        {
            "job_analysis": analysis.model_dump(mode="python"),
            "technical_fit": technical,
            "commercial_fit": commercial,
            "portfolio_fit": portfolio,
            "summary": {
                "summary": summary,
                "key_alignments": ["Test alignment"],
                "key_gaps": ["Test gap"],
            },
        }
    )


def _plan(assessment, match, profile=None):
    return ApplicationStrategyService(DeterministicStrategyPlanner()).plan(
        assessment,
        match,
        profile or minimal_profile(),
    )


def test_normalize_location_strips_hybrid_parenthetical() -> None:
    assert _normalize_location_tokens("Melbourne VIC (Hybrid)") == frozenset(
        {"melbourne", "vic"}
    )
    assert _normalize_location_tokens("Melbourne, VIC") == frozenset(
        {"melbourne", "vic"}
    )


def test_melbourne_vic_matches_melbourne_vic() -> None:
    assert _locations_compatible("Melbourne VIC", "Melbourne, VIC")


def test_melbourne_vic_matches_melbourne_vic_hybrid() -> None:
    assert _locations_compatible("Melbourne VIC (Hybrid)", "Melbourne, VIC")


def test_melbourne_vic_matches_melbourne_victoria() -> None:
    assert _locations_compatible("Melbourne VIC", "Melbourne, Victoria")


def test_melbourne_does_not_match_sydney() -> None:
    assert not _locations_compatible("Sydney NSW", "Melbourne, VIC")
    assert not _locations_compatible("Sydney CBD", "Melbourne, VIC")


def test_remote_australia_preference_matches_remote_australia_job() -> None:
    assert _locations_compatible("Remote Australia", "Remote Australia")


def test_genuine_location_conflict_still_warns() -> None:
    analysis = job_analysis(
        location={
            "clarity": "stated",
            "summary": "Sydney NSW",
            "evidence": [{"excerpt": "Sydney NSW"}],
        },
        work_arrangement={
            "arrangement": "hybrid",
            "evidence": [{"excerpt": "Sydney hybrid"}],
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
            "Location soft concern.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Sydney differs from Melbourne preference.",
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
            "Portfolio supports.",
            [
                _finding(
                    summary="Project aligns.",
                    profile_evidence=[
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Genuine Sydney vs Melbourne mismatch.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    assert any(
        "Location or work-arrangement signals conflict" in risk.summary
        for risk in strategy.risks_or_gaps
    )
    assert any(
        check.summary.startswith("Review location")
        for check in strategy.manual_checks
    )


def test_melbourne_hybrid_does_not_warn_against_melbourne_preference() -> None:
    analysis = job_analysis(
        location={
            "clarity": "stated",
            "summary": "Melbourne VIC (Hybrid)",
            "evidence": [{"excerpt": "Melbourne VIC (Hybrid)"}],
        },
        work_arrangement={
            "arrangement": "hybrid",
            "evidence": [{"excerpt": "Melbourne VIC (Hybrid)"}],
        },
    )
    profile = CareerProfileService.from_path(
        fixtures_dir() / "golden" / "career_profile.yaml"
    ).load()
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "mixed",
            "Mixed technical fit.",
            [_finding(kind="gap", summary="Production LLM gap.")],
        ),
        commercial=_dimension(
            "commercial",
            "strong",
            "Commercial fit strong.",
            [_finding(summary="Compensation ok.")],
        ),
        portfolio=_dimension(
            "portfolio",
            "moderate",
            "Portfolio moderate.",
            [
                _finding(
                    summary="Projects partially align.",
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                )
            ],
        ),
        summary="Melbourne hybrid AI role.",
    )
    match = PortfolioMatchingService(DeterministicMatcher()).match(analysis, profile)
    strategy = _plan(assessment, match, profile)

    assert not any(
        "Location or work-arrangement signals conflict" in risk.summary
        for risk in strategy.risks_or_gaps
    )
    assert not any(
        check.summary.startswith("Review location")
        for check in strategy.manual_checks
    )


def test_role_family_reason_phrase_by_family() -> None:
    assert _role_family_reason_phrase("ai_engineering") == "AI-aligned role family"
    assert (
        _role_family_reason_phrase("software_engineering")
        == "software engineering role family"
    )
    assert (
        _role_family_reason_phrase("data_engineering")
        == "data engineering role family"
    )


def test_software_engineering_strategy_wording_is_not_ai_aligned() -> None:
    analysis = job_analysis(
        posting={
            "raw_text": "Junior Software Engineer. Python preferred. Melbourne VIC.",
            "title": "Junior Software / DevOps Engineer",
            "company": "Example Co",
        },
        role_family={
            "family": "software_engineering",
            "evidence": [{"excerpt": "Junior Software", "section": "Job title"}],
        },
        seniority={
            "level": "entry",
            "ambiguous": False,
            "evidence": [{"excerpt": "Junior", "section": "Job title"}],
        },
        location={
            "clarity": "stated",
            "summary": "Melbourne, VIC",
            "evidence": [{"excerpt": "Melbourne VIC"}],
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
            "weak",
            "Commercial fit weak.",
            [_finding(kind="gap", summary="Salary unstated.")],
        ),
        portfolio=_dimension(
            "portfolio",
            "moderate",
            "Portfolio moderate.",
            [
                _finding(
                    summary="Projects partially align.",
                    profile_evidence=[
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Software engineering adjacent role.",
    )
    strategy = _plan(assessment, portfolio_match(analysis))

    priority_reasons = [
        reason.summary for reason in strategy.reasons if reason.kind == "priority"
    ]
    assert priority_reasons
    assert any("software engineering role family" in text for text in priority_reasons)
    assert not any("AI-aligned role family" in text for text in priority_reasons)


def test_junior_software_fixture_structured_fields() -> None:
    analysis = JobAnalysisService(FixtureExtractor()).analyse(
        posting_junior_software_devops()
    )

    assert analysis.role_family.family == "software_engineering"
    assert analysis.seniority.level == "entry"
    assert analysis.location.summary in {"Melbourne, VIC", "Melbourne VIC"}

    tech_names = {tech.name.casefold() for tech in analysis.technologies}
    assert "python" in tech_names
    assert "linux" in tech_names
    assert "terraform" in tech_names
    assert "ansible" in tech_names
    assert any("database" in name for name in tech_names)
    assert len(analysis.responsibilities) >= 5

    responsibility_blob = " ".join(
        item.description.casefold() for item in analysis.responsibilities
    )
    assert "software" in responsibility_blob
    assert "ci/cd" in responsibility_blob or "cicd" in responsibility_blob.replace(
        "/", ""
    )
    assert "customer" in responsibility_blob
    assert "self-motivated" not in responsibility_blob
    assert "how you match" not in responsibility_blob
