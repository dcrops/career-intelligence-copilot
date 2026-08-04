"""Regression: unsupported JD technologies must not become CV emphasis."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from career_intelligence.application_strategy import ApplicationStrategy
from career_intelligence.cv_generation import (
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
)
from career_intelligence.profile import CareerProfileService

_REPO_ROOT = Path(__file__).resolve().parents[3]
_OUTPUTS = _REPO_ROOT / "manual_validation" / "outputs"
_PROFILE = _REPO_ROOT / "data" / "career_profile.yaml"

# Technologies observed as false summary themes during owner validation.
_UNSUPPORTED_EMPHASIS_EXAMPLES = {
    "002_bluefin_ai_systems_developer.json": frozenset(
        {"Terraform", "PostgreSQL", "Ruby on Rails", "Ruby", "Rails"}
    ),
    "011_officeworks_ai_engineer.json": frozenset(
        {"JavaScript", "TypeScript", "React"}
    ),
    "013_pay_com_au_ai_automation_engineer.json": frozenset(
        {"TypeScript"}
    ),
}


def _load_strategy(name: str) -> ApplicationStrategy:
    payload = json.loads((_OUTPUTS / name).read_text(encoding="utf-8"))
    return ApplicationStrategy.model_validate(payload["application_strategy"])


def _needs_material_benefit_override(strategy: ApplicationStrategy) -> bool:
    """Silver/bronze corpus jobs without consider_cv_tailoring need an explicit override."""
    return strategy.application_tier not in {"platinum", "gold"} and not any(
        action.kind == "consider_cv_tailoring" for action in strategy.next_actions
    )


def _plan_for(name: str, *, override: bool | None = None):
    profile = CareerProfileService.from_path(_PROFILE).load()
    strategy = _load_strategy(name)
    use_override = (
        _needs_material_benefit_override(strategy) if override is None else override
    )
    return TailoringPlanService(DeterministicTailoringPlanner()).plan(
        strategy,
        profile,
        options=TailoringOptions(
            owner_approved_to_tailor=True,
            override_material_benefit=use_override,
        ),
    )


@pytest.mark.parametrize(
    ("output_name", "unsupported"),
    sorted(_UNSUPPORTED_EMPHASIS_EXAMPLES.items()),
)
def test_corpus_jobs_keep_unsupported_out_of_themes_and_promotions(
    output_name: str,
    unsupported: frozenset[str],
) -> None:
    # Silver jobs (e.g. 013) need override to produce a plan; platinum/gold do not.
    plan = _plan_for(output_name)

    themes = {item.theme.casefold() for item in plan.summary_themes}
    promoted = {item.skill_name.casefold() for item in plan.skills_to_promote}
    for label in unsupported:
        assert label.casefold() not in themes, (
            f"{output_name}: unsupported '{label}' must not be a summary theme; "
            f"themes={sorted(themes)}"
        )
        assert label.casefold() not in promoted, (
            f"{output_name}: unsupported '{label}' must not be promoted; "
            f"promoted={sorted(promoted)}"
        )

    # Employer priorities may still list unsupported technologies with status.
    for item in plan.jd_priorities:
        if any(u.casefold() == item.label.casefold() for u in unsupported):
            assert item.candidate_support == "unsupported"


def test_bluefin_keeps_supported_python_and_llm_related_emphasis() -> None:
    # Corpus baseline is platinum Bluefin (committed fixture). Override auto-applies
    # if a live re-run accidentally leaves the JSON silver.
    plan = _plan_for("002_bluefin_ai_systems_developer.json")
    themes = [item.theme for item in plan.summary_themes]
    promoted = [item.skill_name for item in plan.skills_to_promote]
    assert "Terraform" not in themes
    assert "Ruby on Rails" not in themes
    assert "PostgreSQL" not in themes
    # At least one candidate-supported capability remains emphasised.
    assert themes or promoted
    assert all(
        item.candidate_support in {"supported", "related", "unsupported"}
        for item in plan.jd_priorities
    )
    supported_or_related = [
        item for item in plan.jd_priorities if item.candidate_support != "unsupported"
    ]
    assert supported_or_related


def test_officeworks_ranks_python_above_pd_only_snowflake() -> None:
    """Snowflake remains recognised but is not over-prioritised vs employment evidence.

    Relies on the committed Officeworks corpus where Snowflake is among the early
    JD technologies (within ``_MAX_JD_PRIORITIES``). Live re-extraction that appends
    many frontend tokens before Snowflake can push it past the priority cap — restore
    the committed fixture rather than raising the cap.
    """
    plan = _plan_for("011_officeworks_ai_engineer.json")
    themes = [item.theme for item in plan.summary_themes]
    promoted = [item.skill_name for item in plan.skills_to_promote]

    assert "Python" in promoted
    assert "Python" in themes
    if "Snowflake" in promoted:
        assert promoted.index("Python") < promoted.index("Snowflake")
    if "Snowflake" in themes:
        assert themes.index("Python") < themes.index("Snowflake")
    # Truthful recognition: JD priority still lists Snowflake when present in-cap.
    snowflake_priorities = [
        item for item in plan.jd_priorities if item.label.casefold() == "snowflake"
    ]
    assert snowflake_priorities, (
        "expected Snowflake in jd_priorities for committed Officeworks corpus; "
        "if this fails after a live re-run, restore "
        "manual_validation/outputs/011_officeworks_ai_engineer.json from git"
    )
    assert snowflake_priorities[0].candidate_support == "supported"


def test_bluefin_keeps_openai_langchain_emphasis_where_relevant() -> None:
    plan = _plan_for("002_bluefin_ai_systems_developer.json")
    promoted = {item.skill_name.casefold() for item in plan.skills_to_promote}
    themes = {item.theme.casefold() for item in plan.summary_themes}
    combined = promoted | themes
    assert any(
        name in combined
        for name in {
            "openai apis",
            "langchain",
            "llm application development",
            "python",
        }
    )
    assert "ruby on rails" not in combined
    assert "terraform" not in combined


def test_maincode_does_not_lead_with_test_automation_only() -> None:
    """AI Infrastructure sparse JD overlap must not promote Test automation alone."""
    plan = _plan_for(
        "012_maincode_ai_infrastructure_engineer.json",
        override=True,
    )
    themes = [item.theme for item in plan.summary_themes]
    promoted = [item.skill_name for item in plan.skills_to_promote]
    assert "Test automation" not in themes
    assert "Test automation" not in promoted
    assert "Python" in promoted
    assert any(
        name in {t.casefold() for t in themes}
        for name in {
            "python",
            "openai apis",
            "llm application development",
            "operational intelligence",
            "retrieval-augmented generation",
        }
    )


def test_automation_jd_token_does_not_match_test_automation_skill() -> None:
    from career_intelligence.cv_generation.deterministic_planner import _direct_match

    assert _direct_match("automation", "Test automation") is False
    assert _direct_match("Python", "Python Programming") is True
    assert _direct_match("openai", "OpenAI APIs") is True


def test_fixture_rewrite_excludes_unsupported_technologies() -> None:
    """Phase C fixture path must not introduce unsupported JD technologies."""
    from career_intelligence.cv_generation import (
        CvGenerationOptions,
        CvGenerationService,
    )
    from career_intelligence.cv_generation.fixture_summary_rewriter import (
        FixtureSummaryRewriter,
    )
    from career_intelligence.profile import CareerProfileService

    profile = CareerProfileService.from_path(_PROFILE).load()
    for output_name, unsupported in _UNSUPPORTED_EMPHASIS_EXAMPLES.items():
        plan = _plan_for(output_name)
        strategy = _load_strategy(output_name)
        cv = CvGenerationService(FixtureSummaryRewriter()).generate(
            strategy,
            profile,
            plan,
            options=CvGenerationOptions(
                tailoring_plan_approved=True,
                rewrite_summary=True,
            ),
        )
        assert cv.summary_source in {"fixture_rewrite", "fallback_profile_copy", "profile_copy"}
        summary = (cv.summary or "").casefold()
        for label in unsupported:
            assert label.casefold() not in summary, (
                f"{output_name}: rewritten summary must not contain '{label}'; "
                f"summary={cv.summary!r}"
            )

