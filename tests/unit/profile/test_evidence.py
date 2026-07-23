"""Tests for Career Profile evidence-strength resolution and ranking."""

from __future__ import annotations

from career_intelligence.profile import (
    SkillEvidenceRef,
    evidence_strength_rank,
    resolve_skill_evidence_refs,
    strongest_evidence_kind,
    strongest_evidence_kind_for_capability,
)
from career_intelligence.profile.models import ExperienceEntry, Skill
from tests.unit.cv_generation.helpers import minimal_profile


def test_evidence_strength_rank_orders_kinds() -> None:
    assert evidence_strength_rank("employment") < evidence_strength_rank(
        "independent_engineering"
    )
    assert evidence_strength_rank("independent_engineering") < evidence_strength_rank(
        "portfolio_project"
    )
    assert evidence_strength_rank("portfolio_project") < evidence_strength_rank(
        "certification"
    )
    assert evidence_strength_rank("certification") < evidence_strength_rank(
        "professional_development"
    )
    assert evidence_strength_rank("professional_development") < evidence_strength_rank(
        "coursework"
    )
    assert evidence_strength_rank("coursework") < evidence_strength_rank("unspecified")


def test_legacy_evidence_resolves_experience_kind() -> None:
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
                        Skill(
                            name="Python",
                            evidence="experience:example-role",
                        ),
                        Skill(
                            name="Snowflake",
                            evidence="experience:pd-data-eng",
                        ),
                        Skill(
                            name="FastAPI",
                            evidence="project:example-project",
                        ),
                    ]
                }
            ),
        }
    )
    python = profile.skills.technical[0]
    snowflake = profile.skills.technical[1]
    fastapi = profile.skills.technical[2]

    assert strongest_evidence_kind(profile, python) == "employment"
    assert strongest_evidence_kind(profile, snowflake) == "professional_development"
    assert strongest_evidence_kind(profile, fastapi) == "portfolio_project"

    refs = resolve_skill_evidence_refs(profile, snowflake)
    assert refs == [
        SkillEvidenceRef(kind="professional_development", ref="experience:pd-data-eng")
    ]


def test_explicit_evidence_refs_take_precedence_over_legacy() -> None:
    profile = minimal_profile()
    skill = Skill(
        name="Databricks",
        evidence="experience:example-role",
        evidence_refs=[
            SkillEvidenceRef(
                kind="certification",
                ref="certification:databricks-associate",
            )
        ],
    )
    assert resolve_skill_evidence_refs(profile, skill)[0].kind == "certification"
    assert strongest_evidence_kind(profile, skill) == "certification"


def test_strongest_evidence_prefers_employment_over_pd() -> None:
    profile = minimal_profile()
    pd = ExperienceEntry.model_validate(
        {
            "id": "pd-python",
            "kind": "professional_development",
            "organisation": "Independent study",
            "title": "Python study",
            "start_date": "2024-01",
            "end_date": "2024-06",
            "highlights": ["Studied Python"],
            "technologies": ["Python"],
        }
    )
    profile = profile.model_copy(update={"experience": [*profile.experience, pd]})
    skill = Skill(
        name="Python",
        evidence="experience:pd-python; experience:example-role",
    )
    assert strongest_evidence_kind(profile, skill) == "employment"


def test_capability_name_falls_back_to_project_technology() -> None:
    profile = minimal_profile()
    # Drop skill rows so only project technologies remain as evidence.
    profile = profile.model_copy(
        update={"skills": profile.skills.model_copy(update={"technical": [
            Skill(name="Unrelated", evidence=None),
        ]})}
    )
    assert strongest_evidence_kind_for_capability(profile, "Python") == (
        "portfolio_project"
    )
