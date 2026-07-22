"""Shared builders for FR-005 Phase A unit tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile import CareerProfile, CareerProfileService


def fixtures_dir() -> Path:
    return Path(__file__).parents[2] / "fixtures"


def minimal_profile() -> CareerProfile:
    return CareerProfileService.from_path(
        fixtures_dir() / "minimal_valid_profile.yaml"
    ).load()


def job_analysis_payload(**overrides: object) -> dict[str, object]:
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
    return payload


def job_analysis(**overrides: object) -> JobAnalysis:
    return JobAnalysis.model_validate(job_analysis_payload(**overrides))


def assessment_payload(
    analysis: JobAnalysis | None = None,
    **overrides: object,
) -> dict[str, object]:
    bound = analysis or job_analysis()
    payload: dict[str, object] = {
        "job_analysis": bound.model_dump(mode="json"),
        "technical_fit": {
            "dimension": "technical",
            "judgment": "strong",
            "summary": "Strong technical alignment on Python.",
            "findings": [
                {
                    "kind": "alignment",
                    "summary": "Required Python aligns with profile skills.",
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
            "summary": "Commercial fit is broadly compatible.",
            "findings": [
                {
                    "kind": "alignment",
                    "summary": "Melbourne hybrid aligns with location preferences.",
                    "importance": "material",
                    "job_evidence": [{"source": "location"}],
                    "profile_evidence": [
                        {"source": "preference", "ref": "preference:locations"}
                    ],
                }
            ],
        },
        "portfolio_fit": {
            "dimension": "portfolio",
            "judgment": "moderate",
            "summary": "Portfolio supports an AI engineering narrative.",
            "findings": [
                {
                    "kind": "alignment",
                    "summary": "Example project demonstrates relevant capability.",
                    "importance": "material",
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
                            "ref": "project:example-project",
                        }
                    ],
                }
            ],
        },
        "summary": {
            "summary": "Strong AI Engineer alignment with moderate commercial fit.",
            "key_alignments": ["Python", "AI engineering direction"],
            "key_gaps": [],
        },
    }
    payload.update(overrides)
    return payload


def opportunity_assessment(
    analysis: JobAnalysis | None = None,
    **overrides: object,
) -> OpportunityAssessment:
    return OpportunityAssessment.model_validate(
        assessment_payload(analysis, **overrides)
    )


def portfolio_match_payload(
    analysis: JobAnalysis | None = None,
    *,
    project_id: str = "example-project",
    **overrides: object,
) -> dict[str, object]:
    bound = analysis or job_analysis()
    payload: dict[str, object] = {
        "job_analysis": bound.model_dump(mode="json"),
        "ranked_projects": [
            {
                "rank": 1,
                "project_id": project_id,
                "rationale": f"Lead with {project_id} for required Python.",
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
        "unranked_project_ids": [],
        "summary": f"Lead with {project_id}.",
        "insufficient_evidence": False,
    }
    payload.update(overrides)
    return payload


def portfolio_match(
    analysis: JobAnalysis | None = None,
    *,
    project_id: str = "example-project",
    **overrides: object,
) -> PortfolioMatch:
    return PortfolioMatch.model_validate(
        portfolio_match_payload(analysis, project_id=project_id, **overrides)
    )


def assessment_evidence(
    *,
    dimension: str = "technical",
    judgment: str = "strong",
) -> dict[str, object]:
    return {
        "origin": "opportunity_assessment",
        "assessment_dimension": dimension,
        "assessment_judgment": judgment,
    }


def job_tech_evidence() -> dict[str, object]:
    return {
        "origin": "job_analysis",
        "job_evidence": {
            "source": "technology",
            "item_index": 0,
            "name": "Python",
            "excerpt": "Python required",
        },
    }


def profile_skill_evidence() -> dict[str, object]:
    return {
        "origin": "career_profile",
        "profile_evidence": {"source": "skill", "ref": "skill:Python"},
    }


def portfolio_project_evidence(
    project_id: str = "example-project",
) -> dict[str, object]:
    return {
        "origin": "portfolio_match",
        "portfolio_project_id": project_id,
    }


def valid_strategy_payload(**overrides: object) -> dict[str, object]:
    """Untrusted planner payload fields (no job_analysis)."""
    payload: dict[str, object] = {
        "application_tier": "platinum",
        "pursuit_posture": "prioritise",
        "practical_value": "career_priority",
        "effort_level": "full",
        "summary": "Prioritise this AI Engineer opportunity with full effort.",
        "reasons": [
            {
                "kind": "alignment",
                "summary": "Technical fit is strong for an AI Engineering role.",
                "importance": "material",
                "evidence": [assessment_evidence()],
            }
        ],
        "risks_or_gaps": [
            {
                "summary": "Compensation is unstated and should be reviewed.",
                "importance": "minor",
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {"source": "compensation"},
                    }
                ],
            }
        ],
        "manual_checks": [
            {
                "summary": "Confirm compensation once disclosed.",
                "why_it_matters": "Salary clarity could change commercial priority.",
                "could_change_recommendation": True,
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {"source": "compensation"},
                    }
                ],
            }
        ],
        "next_actions": [
            {
                "kind": "consider_emphasising_portfolio_projects",
                "summary": "Consider emphasising example-project in the application.",
                "related_project_id": "example-project",
                "evidence": [portfolio_project_evidence()],
            },
            {
                "kind": "consider_cv_tailoring",
                "summary": "Consider whether CV tailoring is worth the effort.",
                "evidence": [assessment_evidence()],
            },
            {
                "kind": "consider_owner_review",
                "summary": "Review this strategy before taking any external action.",
                "evidence": [assessment_evidence()],
            },
        ],
        "portfolio_emphasis": [
            {
                "project_id": "example-project",
                "source_rank": 1,
                "summary": "Lead with example-project for required Python overlap.",
                "evidence": [portfolio_project_evidence()],
            }
        ],
        "assumptions": [
            "Compensation remains compatible once disclosed.",
        ],
        "decision_blockers": [],
        "owner_review_required": True,
        "insufficient_information": False,
    }
    payload.update(overrides)
    return payload
