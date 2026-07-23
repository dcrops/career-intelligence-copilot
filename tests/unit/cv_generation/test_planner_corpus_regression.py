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


def _plan_for(name: str, *, override: bool = False):
    profile = CareerProfileService.from_path(_PROFILE).load()
    strategy = _load_strategy(name)
    return TailoringPlanService(DeterministicTailoringPlanner()).plan(
        strategy,
        profile,
        options=TailoringOptions(
            owner_approved_to_tailor=True,
            override_material_benefit=override,
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
    strategy = _load_strategy(output_name)
    override = strategy.application_tier not in {"platinum", "gold"} and not any(
        action.kind == "consider_cv_tailoring" for action in strategy.next_actions
    )
    plan = _plan_for(output_name, override=override)

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
    """Snowflake remains recognised but is not over-prioritised vs employment evidence."""
    strategy = _load_strategy("011_officeworks_ai_engineer.json")
    override = strategy.application_tier not in {"platinum", "gold"} and not any(
        action.kind == "consider_cv_tailoring" for action in strategy.next_actions
    )
    plan = _plan_for("011_officeworks_ai_engineer.json", override=override)
    themes = [item.theme for item in plan.summary_themes]
    promoted = [item.skill_name for item in plan.skills_to_promote]

    assert "Python" in promoted
    assert "Python" in themes
    if "Snowflake" in promoted:
        assert promoted.index("Python") < promoted.index("Snowflake")
    if "Snowflake" in themes:
        assert themes.index("Python") < themes.index("Snowflake")
    # Truthful recognition: JD priority still lists Snowflake when present.
    snowflake_priorities = [
        item for item in plan.jd_priorities if item.label.casefold() == "snowflake"
    ]
    assert snowflake_priorities
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
        strategy = _load_strategy(output_name)
        override = strategy.application_tier not in {"platinum", "gold"} and not any(
            action.kind == "consider_cv_tailoring" for action in strategy.next_actions
        )
        plan = _plan_for(output_name, override=override)
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

