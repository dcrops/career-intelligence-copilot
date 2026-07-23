"""Unit tests for DeterministicTailoringPlanner."""

from __future__ import annotations

from career_intelligence.cv_generation import (
    DeterministicTailoringPlanner,
    TailoringOptions,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import ExperienceEntry, Skill
from tests.unit.application_strategy.helpers import job_analysis_payload
from tests.unit.cv_generation.helpers import (
    minimal_profile,
    rich_job_analysis,
    strategy_from_payload,
)


def test_planner_promotes_overlapping_skills_in_required_then_preferred_order() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="FastAPI", evidence=None),
                        Skill(name="Docker", evidence=None),
                        Skill(name="Spark", evidence=None),
                    ]
                }
            )
        }
    )
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    payload = DeterministicTailoringPlanner().plan(
        strategy,
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    promoted = [item["skill_name"] for item in payload["skills_to_promote"]]
    assert promoted == ["Python", "FastAPI", "Docker"]
    not_emphasised = [item["skill_name"] for item in payload["skills_not_emphasised"]]
    assert "Spark" in not_emphasised
    assert "TensorFlow" not in promoted  # not on profile


def test_evidence_strength_ranks_employment_above_professional_development() -> None:
    """PD-only skills stay truthful but rank below employment/portfolio evidence."""
    profile = minimal_profile()
    pd = ExperienceEntry.model_validate(
        {
            "id": "pd-data-eng",
            "kind": "professional_development",
            "organisation": "Independent study",
            "title": "Data Engineering Upskilling",
            "start_date": "2023-10",
            "end_date": "2025-06",
            "highlights": ["Studied Snowflake"],
            "technologies": ["Snowflake"],
        }
    )
    profile = profile.model_copy(
        update={
            "experience": [*profile.experience, pd],
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Snowflake", evidence="experience:pd-data-eng"),
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(
                            name="FastAPI",
                            evidence="project:example-project",
                        ),
                    ]
                }
            ),
        }
    )
    # List Snowflake before Python in the JD so ranking is evidence-driven, not
    # discovery-order-driven.
    analysis = JobAnalysis.model_validate(
        job_analysis_payload(
            technologies=[
                {
                    "name": "Snowflake",
                    "level": "required",
                    "evidence": [
                        {"excerpt": "Snowflake required", "section": "requirements"}
                    ],
                },
                {
                    "name": "Python",
                    "level": "required",
                    "evidence": [
                        {"excerpt": "Python required", "section": "requirements"}
                    ],
                },
                {
                    "name": "FastAPI",
                    "level": "required",
                    "evidence": [
                        {"excerpt": "FastAPI required", "section": "requirements"}
                    ],
                },
            ]
        )
    )
    payload = DeterministicTailoringPlanner().plan(
        strategy_from_payload(job_analysis=analysis),
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    promoted = [item["skill_name"] for item in payload["skills_to_promote"]]
    themes = [item["theme"] for item in payload["summary_themes"]]

    assert "Snowflake" in promoted
    assert promoted.index("Python") < promoted.index("Snowflake")
    assert promoted.index("FastAPI") < promoted.index("Snowflake")
    assert "Snowflake" in themes
    assert themes.index("Python") < themes.index("Snowflake")

    snowflake_skill = next(
        item for item in payload["skills_to_promote"] if item["skill_name"] == "Snowflake"
    )
    assert "professional development" in snowflake_skill["rationale"].casefold()


def test_planner_follows_portfolio_emphasis_order() -> None:
    profile = minimal_profile()
    second = profile.projects[0].model_copy(
        update={"id": "second-project", "name": "Second Project"}
    )
    profile = profile.model_copy(update={"projects": [*profile.projects, second]})
    strategy = strategy_from_payload(
        portfolio_emphasis=[
            {
                "project_id": "second-project",
                "source_rank": 1,
                "summary": "Lead with second-project.",
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": "second-project",
                    }
                ],
            },
            {
                "project_id": "example-project",
                "source_rank": 2,
                "summary": "Then example-project.",
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": "example-project",
                    }
                ],
            },
        ],
        next_actions=[
            {
                "kind": "consider_cv_tailoring",
                "summary": "Consider CV tailoring.",
                "evidence": [
                    {
                        "origin": "opportunity_assessment",
                        "assessment_dimension": "technical",
                        "assessment_judgment": "strong",
                    }
                ],
            },
            {
                "kind": "consider_owner_review",
                "summary": "Review strategy.",
                "evidence": [
                    {
                        "origin": "opportunity_assessment",
                        "assessment_dimension": "technical",
                        "assessment_judgment": "strong",
                    }
                ],
            },
        ],
    )
    payload = DeterministicTailoringPlanner().plan(
        strategy,
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    assert [item["project_id"] for item in payload["projects_to_emphasise"]] == [
        "second-project",
        "example-project",
    ]


def test_planner_builds_jd_priorities_from_required_technologies_first() -> None:
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    payload = DeterministicTailoringPlanner().plan(
        strategy,
        minimal_profile(),
        TailoringOptions(owner_approved_to_tailor=True),
    )
    labels = [item["label"] for item in payload["jd_priorities"]]
    assert labels[0] == "Python"
    assert labels[1] == "FastAPI"
    assert "Docker" in labels
    by_label = {item["label"]: item for item in payload["jd_priorities"]}
    assert by_label["Python"]["candidate_support"] == "supported"
    assert by_label["TensorFlow"]["candidate_support"] == "unsupported"


def test_summary_themes_exclude_unsupported_jd_technologies() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="FastAPI", evidence=None),
                        Skill(name="Docker", evidence=None),
                    ]
                }
            )
        }
    )
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    payload = DeterministicTailoringPlanner().plan(
        strategy,
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    themes = [item["theme"] for item in payload["summary_themes"]]
    assert "Python" in themes
    assert "FastAPI" in themes
    assert "TensorFlow" not in themes
    assert "Spark" not in themes
    promoted = [item["skill_name"] for item in payload["skills_to_promote"]]
    assert "TensorFlow" not in promoted
    assert all(
        "Career Profile" in item["rationale"] or "evidenced" in item["rationale"]
        for item in payload["skills_to_promote"]
    )


def test_related_llm_maps_to_profile_openai_without_unsupported_theme() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="OpenAI APIs", evidence=None),
                        Skill(name="LangChain", evidence=None),
                    ]
                }
            )
        }
    )
    analysis = JobAnalysis.model_validate(
        job_analysis_payload(
            technologies=[
                {
                    "name": "LLM",
                    "level": "required",
                    "evidence": [{"excerpt": "LLM experience", "section": "requirements"}],
                },
                {
                    "name": "Ruby on Rails",
                    "level": "preferred",
                    "evidence": [{"excerpt": "Rails", "section": "requirements"}],
                },
            ]
        )
    )
    strategy = strategy_from_payload(job_analysis=analysis)
    payload = DeterministicTailoringPlanner().plan(
        strategy,
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    by_label = {item["label"]: item for item in payload["jd_priorities"]}
    assert by_label["LLM"]["candidate_support"] == "related"
    assert by_label["Ruby on Rails"]["candidate_support"] == "unsupported"
    themes = [item["theme"] for item in payload["summary_themes"]]
    assert "Ruby on Rails" not in themes
    assert any(theme in {"OpenAI APIs", "LangChain"} for theme in themes)
    promoted = [item["skill_name"] for item in payload["skills_to_promote"]]
    assert "Ruby on Rails" not in promoted
    assert "OpenAI APIs" in promoted or "LangChain" in promoted


def test_planner_is_deterministic() -> None:
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    profile = minimal_profile()
    options = TailoringOptions(owner_approved_to_tailor=True)
    planner = DeterministicTailoringPlanner()
    first = planner.plan(strategy, profile, options)
    second = planner.plan(strategy, profile, options)
    assert first == second


def test_planner_defaults_to_master_cv_experience_scope() -> None:
    from tests.unit.cv_generation.helpers import profile_with_extended_history

    profile = profile_with_extended_history()
    payload = DeterministicTailoringPlanner().plan(
        strategy_from_payload(),
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    guidance = payload["experience_guidance"]
    assert guidance["kind"] == "master_cv_only"
    assert "bakers-delight-test-analyst-2009" in guidance["excluded_experience_ids"]
    assert "example-role" in guidance["included_experience_ids"]
