"""Deterministic cover-letter opening strategy selection (FR-007 polish).

Package-private. Composer owns prose; this module only chooses a strategy and
supplies stable inputs. Same plan + profile always yield the same strategy.
"""

from __future__ import annotations

from typing import Literal

from career_intelligence.cover_letter.models import CoverLetterPlan
from career_intelligence.profile.models import CareerProfile

OpeningStrategy = Literal[
    "experience_led",
    "technology_led",
    "business_problem_led",
    "organisation_led",
    "career_transition_led",
    "mission_capability_led",
]

# Tie-break order when scores are equal — fixed, never random.
_STRATEGY_PRIORITY: tuple[OpeningStrategy, ...] = (
    "business_problem_led",
    "technology_led",
    "experience_led",
    "mission_capability_led",
    "organisation_led",
    "career_transition_led",
)

_RETAIL_ORG_CUES = (
    "fashion",
    "retail",
    "e-commerce",
    "ecommerce",
    "clothing",
    "consumer",
    "fmcg",
    "store",
)

_TECH_CUES = (
    "python",
    "fastapi",
    "llm",
    "llms",
    "rag",
    "retrieval",
    "agent",
    "azure",
    "docker",
    "api",
    "databricks",
    "openai",
)


def select_opening_strategy(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    *,
    employer_mode: str,
) -> OpeningStrategy:
    """Score opening strategies from role, employer, evidence, and profile."""
    scores: dict[OpeningStrategy, int] = {name: 0 for name in _STRATEGY_PRIORITY}
    family = plan.job_analysis.role_family.family
    company = (plan.company_alignment.company or "").casefold()
    raw = (plan.job_analysis.posting.raw_text or "").casefold()
    hook = (plan.company_alignment.alignment_hook or "").casefold()
    motivation = (plan.role_motivation.motivation or "").casefold()
    tech_names = [
        tech.name.casefold() for tech in plan.job_analysis.technologies
    ]
    project_ids = [item.project_id for item in plan.strongest_projects]

    if family in {"ai_engineering", "ai_adjacent", "ml_engineering", "ai_solutions"}:
        scores["technology_led"] += 2
        scores["mission_capability_led"] += 2
        scores["experience_led"] += 1
    if family in {"software_engineering", "data_engineering"}:
        scores["technology_led"] += 2
        scores["experience_led"] += 2
    if family == "data_engineering":
        scores["career_transition_led"] += 1

    if employer_mode == "recruiter":
        scores["business_problem_led"] += 2
        scores["technology_led"] += 2
        scores["organisation_led"] -= 1
    else:
        scores["organisation_led"] += 2

    retailish = any(cue in company or cue in raw for cue in _RETAIL_ORG_CUES)
    if retailish:
        scores["business_problem_led"] += 3
        scores["organisation_led"] += 2
        scores["technology_led"] += 1
        # Direct retail/product brands open on the organisation, not the stack.
        if employer_mode == "direct":
            scores["organisation_led"] += 3

    tech_hits = sum(1 for name in tech_names if any(cue in name for cue in _TECH_CUES))
    if tech_hits >= 3:
        scores["technology_led"] += 3
    elif tech_hits >= 1:
        scores["technology_led"] += 1

    if any(token in hook or token in motivation for token in ("automati", "operat", "deploy", "product")):
        scores["business_problem_led"] += 2

    ai_projects = {
        "career-intelligence-copilot",
        "governance-document-rag",
        "operational-intelligence-copilot",
    }
    if any(project_id in ai_projects for project_id in project_ids):
        scores["experience_led"] += 2
        scores["mission_capability_led"] += 1

    if _profile_shows_career_transition(profile):
        scores["career_transition_led"] += 4

    # Prefer organisation-led when the company is a known product brand (not a recruiter).
    if employer_mode == "direct" and company and "partner" not in company:
        scores["organisation_led"] += 1

    best = max(scores.values())
    for name in _STRATEGY_PRIORITY:
        if scores[name] == best:
            return name
    return "experience_led"


def _profile_shows_career_transition(profile: CareerProfile) -> bool:
    kinds = {entry.kind for entry in profile.experience}
    titles = " ".join(entry.title.casefold() for entry in profile.experience)
    has_de = any(
        "data engineer" in (entry.title or "").casefold()
        or entry.kind == "professional_development"
        and "data engineering" in (entry.title or "").casefold()
        for entry in profile.experience
    )
    has_ai = (
        "independent_engineering" in kinds
        or "ai engineer" in titles
        or "ai engineering" in titles
    )
    return has_de and has_ai


def leading_technologies(plan: CoverLetterPlan, *, limit: int = 3) -> list[str]:
    """JD technologies suitable for a technology-led opening."""
    names: list[str] = []
    for tech in plan.job_analysis.technologies:
        label = tech.name.strip()
        if not label:
            continue
        folded = label.casefold()
        if folded in {item.casefold() for item in names}:
            continue
        names.append(label)
        if len(names) >= limit:
            break
    return names


def lead_project_name(plan: CoverLetterPlan) -> str | None:
    if not plan.strongest_projects:
        return None
    return plan.strongest_projects[0].project_name
