"""Unit tests for PortfolioMatchingService trust-boundary behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.portfolio_matching import (
    PortfolioMatch,
    PortfolioMatchingError,
    PortfolioMatchingService,
    PortfolioMatchingValidationError,
)
from career_intelligence.portfolio_matching.matcher import PortfolioMatchPayload
from career_intelligence.profile import CareerProfile, CareerProfileService


def _fixtures_dir() -> Path:
    return Path(__file__).parents[2] / "fixtures"


def _minimal_profile() -> CareerProfile:
    return CareerProfileService.from_path(
        _fixtures_dir() / "minimal_valid_profile.yaml"
    ).load()


def _golden_profile() -> CareerProfile:
    return CareerProfileService.from_path(
        _fixtures_dir() / "golden" / "career_profile.yaml"
    ).load()


def _job_analysis() -> JobAnalysis:
    return JobAnalysis.model_validate(
        {
            "posting": {
                "raw_text": "Senior AI Engineer. Python required. Hybrid Melbourne.",
                "title": "Senior AI Engineer",
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
                    "evidence": [
                        {"excerpt": "Python required", "section": "requirements"}
                    ],
                }
            ],
            "responsibilities": [],
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
    )


def _factor_for(project_id: str) -> dict[str, object]:
    return {
        "kind": "required_technology",
        "summary": f"{project_id} uses required Python.",
        "job_evidence": [
            {
                "source": "technology",
                "item_index": 0,
                "name": "Python",
                "excerpt": "Python required",
            }
        ],
        "profile_evidence": [{"source": "project", "ref": f"project:{project_id}"}],
    }


def _match_payload_for_profile(
    profile: CareerProfile,
    *,
    lead_project_id: str | None = None,
) -> dict[str, object]:
    project_ids = [entry.id for entry in profile.projects]
    lead = lead_project_id or project_ids[0]
    remaining = [project_id for project_id in project_ids if project_id != lead]
    return {
        "ranked_projects": [
            {
                "rank": 1,
                "project_id": lead,
                "rationale": f"Lead with {lead} for this role.",
                "factors": [_factor_for(lead)],
            }
        ],
        "unranked_project_ids": remaining,
        "summary": f"Lead with {lead}; remaining projects lack stronger overlap.",
        "insufficient_evidence": False,
    }


class _StaticPayloadMatcher:
    def __init__(self, payload: PortfolioMatchPayload) -> None:
        self._payload = payload

    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatchPayload:
        _ = job_analysis, profile
        return self._payload


class _FailingMatcher:
    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatchPayload:
        _ = job_analysis, profile
        raise PortfolioMatchingError("matcher failed")


def test_service_requires_a_matcher() -> None:
    with pytest.raises(TypeError):
        PortfolioMatchingService()  # type: ignore[call-arg]


def test_valid_payload_becomes_trusted_portfolio_match() -> None:
    profile = _minimal_profile()
    job_analysis = _job_analysis()
    service = PortfolioMatchingService(
        _StaticPayloadMatcher(_match_payload_for_profile(profile))
    )

    match = service.match(job_analysis, profile)

    assert isinstance(match, PortfolioMatch)
    assert match.ranked_projects[0].project_id == "example-project"
    assert match.unranked_project_ids == []


def test_returned_match_contains_exact_original_job_analysis() -> None:
    profile = _minimal_profile()
    job_analysis = _job_analysis()
    match = PortfolioMatchingService(
        _StaticPayloadMatcher(_match_payload_for_profile(profile))
    ).match(job_analysis, profile)

    assert match.job_analysis is job_analysis


def test_matcher_payload_cannot_replace_input_job_analysis() -> None:
    profile = _minimal_profile()
    caller_analysis = _job_analysis()
    other_analysis = JobAnalysis.model_validate(
        {
            "posting": {"raw_text": "Other posting that must not replace caller input."},
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
        }
    )
    payload = _match_payload_for_profile(profile)
    payload["job_analysis"] = other_analysis.model_dump(mode="python")
    service = PortfolioMatchingService(_StaticPayloadMatcher(payload))

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(caller_analysis, profile)

    assert any(error.loc == ("job_analysis",) for error in raised.value.errors)


def test_matcher_payload_cannot_embed_profile() -> None:
    profile = _minimal_profile()
    payload = _match_payload_for_profile(profile)
    payload["profile"] = profile.model_dump(mode="python")
    service = PortfolioMatchingService(_StaticPayloadMatcher(payload))

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(_job_analysis(), profile)

    assert any(error.loc == ("profile",) for error in raised.value.errors)


def test_matcher_payload_cannot_embed_career_profile() -> None:
    profile = _minimal_profile()
    payload = _match_payload_for_profile(profile)
    payload["career_profile"] = profile.model_dump(mode="python")
    service = PortfolioMatchingService(_StaticPayloadMatcher(payload))

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(_job_analysis(), profile)

    assert any(error.loc == ("career_profile",) for error in raised.value.errors)


def test_invalid_schema_becomes_validation_error() -> None:
    service = PortfolioMatchingService(
        _StaticPayloadMatcher(
            {
                "ranked_projects": [],
                "unranked_project_ids": [],
                "insufficient_evidence": False,
            }
        )
    )

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(_job_analysis(), _minimal_profile())

    assert raised.value.errors


def test_unknown_project_reference_is_rejected() -> None:
    profile = _minimal_profile()
    payload = _match_payload_for_profile(profile)
    payload["ranked_projects"] = [
        {
            "rank": 1,
            "project_id": "example-project",
            "rationale": "Invalid nested project reference.",
            "factors": [
                {
                    "kind": "required_technology",
                    "summary": "Cites unknown project.",
                    "job_evidence": [{"source": "technology", "item_index": 0}],
                    "profile_evidence": [
                        {"source": "project", "ref": "project:does-not-exist"}
                    ],
                }
            ],
        }
    ]
    service = PortfolioMatchingService(_StaticPayloadMatcher(payload))

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(_job_analysis(), profile)

    assert any("unknown project id" in error.msg for error in raised.value.errors)


def test_out_of_range_technology_index_is_rejected() -> None:
    profile = _minimal_profile()
    payload = _match_payload_for_profile(profile)
    payload["ranked_projects"] = [
        {
            "rank": 1,
            "project_id": "example-project",
            "rationale": "Invalid technology index.",
            "factors": [
                {
                    "kind": "required_technology",
                    "summary": "Out of range index.",
                    "job_evidence": [{"source": "technology", "item_index": 99}],
                    "profile_evidence": [
                        {"source": "project", "ref": "project:example-project"}
                    ],
                }
            ],
        }
    ]
    service = PortfolioMatchingService(_StaticPayloadMatcher(payload))

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(_job_analysis(), profile)

    assert any("out of range" in error.msg for error in raised.value.errors)


def test_incomplete_project_coverage_is_rejected() -> None:
    profile = _golden_profile()
    payload = {
        "ranked_projects": [
            {
                "rank": 1,
                "project_id": "governance-document-rag",
                "rationale": "Strong RAG overlap.",
                "factors": [_factor_for("governance-document-rag")],
            }
        ],
        "unranked_project_ids": [],
        "summary": "Incomplete coverage.",
        "insufficient_evidence": False,
    }
    service = PortfolioMatchingService(_StaticPayloadMatcher(payload))

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(_job_analysis(), profile)

    assert any("missing project id" in error.msg for error in raised.value.errors)


def test_matcher_errors_propagate() -> None:
    service = PortfolioMatchingService(_FailingMatcher())

    with pytest.raises(PortfolioMatchingError, match="matcher failed"):
        service.match(_job_analysis(), _minimal_profile())


def test_golden_profile_full_coverage_succeeds() -> None:
    profile = _golden_profile()
    job_analysis = _job_analysis()
    service = PortfolioMatchingService(
        _StaticPayloadMatcher(
            _match_payload_for_profile(
                profile,
                lead_project_id="governance-document-rag",
            )
        )
    )

    match = service.match(job_analysis, profile)

    assert match.ranked_projects[0].project_id == "governance-document-rag"
    assert len(match.ranked_projects) + len(match.unranked_project_ids) == len(
        profile.projects
    )
