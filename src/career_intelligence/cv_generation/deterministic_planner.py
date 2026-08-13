"""Deterministic TailoringPlan planner for FR-006 Phase A.

Package-private production path. Returns an untrusted payload; callers must
obtain trusted output through TailoringPlanService.

Owns emphasis decisions only. Does not generate CV prose or re-rank portfolio
projects beyond ApplicationStrategy.portfolio_emphasis order.

Separates three concerns:
- JD requirements (employer priorities) — always listed when present
- Candidate evidence (Career Profile capabilities)
- Tailoring treatment — only supported/related capabilities become promoted
  skills or summary themes; unsupported priorities remain gaps/hiring signals
"""

from __future__ import annotations

import re
from typing import Any, Literal

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis, TechnologyRequirement
from career_intelligence.profile.models import CareerProfile, Skill

from .experience_scope import partition_experience_ids
from .options import TailoringOptions
from .planner import TailoringPlanPayload

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_MAX_JD_PRIORITIES = 8
_MAX_SUMMARY_THEMES = 5
_MAX_PROMOTED_SKILLS = 12
_MIN_PROMOTED_SKILLS_FOR_AI_FAMILY = 4

CandidateSupport = Literal["supported", "related", "unsupported"]

# Single-token JD labels may extend into multi-token profile skills only when
# the extra tokens are benign tech qualifiers (python → python programming).
# Domain qualifiers such as "test" in "test automation" must not match a bare
# JD token like "automation".
_TECH_EXTENSION_TOKENS = frozenset(
    {
        "programming",
        "program",
        "apis",
        "api",
        "sdk",
        "cli",
        "framework",
        "library",
        "server",
        "db",
        "database",
        "sql",
        "lang",
        "language",
    }
)

# When JD tech overlap is sparse (e.g. GPU/infra roles), seed emphasis from
# profile-backed AI Engineering anchors so the CV still leads with truthful,
# role-family-relevant strengths instead of a weak residual match.
_ROLE_FAMILY_PROFILE_ANCHORS: dict[str, tuple[str, ...]] = {
    "ai_engineering": (
        "Python",
        "FastAPI",
        "OpenAI APIs",
        "LLM application development",
        "Retrieval-Augmented Generation",
        "Operational intelligence",
        "Architecture-first design",
        "Human-in-the-loop validation",
        "Docker",
        "PyTest",
        "Git",
        "REST APIs",
    ),
    "ai_adjacent": (
        "LLM application development",
        "Operational intelligence",
        "Explainable AI",
        "Enterprise decision support",
        "Human-in-the-loop validation",
        "OpenAI APIs",
        "Python",
        "Architecture-first design",
        "Agile collaboration",
    ),
}

# Bidirectional related-capability groups (normalised token phrases).
# Exact / containment matches are classified as supported before these apply.
_RELATED_CAPABILITY_GROUPS: tuple[frozenset[str], ...] = (
    frozenset(
        {
            "llm",
            "llms",
            "openai",
            "openai apis",
            "openai api",
            "langchain",
            "gpt",
            "azure openai",
            "llm application development",
            "retrieval augmented generation",
        }
    ),
    frozenset(
        {
            "rest",
            "rest apis",
            "rest api",
            "api",
            "apis",
            "fastapi",
            "backend services",
            "backend service",
        }
    ),
    frozenset(
        {
            "azure",
            "azure data factory",
            "microsoft fabric",
            "data factory",
        }
    ),
    frozenset(
        {
            "docker",
            "containers",
            "container",
            "containerisation",
            "containerization",
        }
    ),
    frozenset(
        {
            "ci cd",
            "cicd",
            "continuous integration",
            "continuous delivery",
            "jenkins",
            "deployment",
            "deploy",
        }
    ),
    frozenset(
        {
            "observability",
            "monitoring",
            "cloudwatch",
            "logging",
            "production support",
        }
    ),
    frozenset(
        {
            "data pipeline",
            "data pipelines",
            "etl",
            "azure data factory",
            "pipeline",
            "pipelines",
        }
    ),
    frozenset(
        {
            "ai engineering",
            "ai engineer",
            "applied ai",
            "production ai",
            "operational intelligence",
            "explainable ai",
        }
    ),
)

# Portfolio signals that indicate AI systems / orchestration engineering.
_AI_PROJECT_CAPABILITY_HINTS: tuple[str, ...] = (
    "llm",
    "openai",
    "rag",
    "retrieval",
    "orchestration",
    "agent",
    "agentic",
    "architecture",
    "evaluation",
    "decision support",
    "human-in-the-loop",
    "fastapi",
    "pydantic",
    "explainable",
)


class DeterministicTailoringPlanner:
    """Build evidence-backed TailoringPlan fields from trusted upstream artifacts.

    Not exported as a public default — inject explicitly into TailoringPlanService.
    """

    def plan(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        options: TailoringOptions,
    ) -> TailoringPlanPayload:
        job = strategy.job_analysis
        assumptions: list[str] = []
        profile_caps = _profile_capabilities(profile)

        jd_priorities = _build_jd_priorities(job, profile, profile_caps)
        promoted, not_emphasised = _build_skills(
            job, profile, profile_caps, assumptions
        )
        promoted, not_emphasised = _ensure_role_family_skill_anchors(
            job, profile, promoted, not_emphasised, assumptions
        )
        themes = _build_summary_themes(job, jd_priorities, profile, assumptions)
        themes = _ensure_role_family_theme_anchors(
            job, profile, themes, promoted, assumptions
        )
        projects = _build_projects(
            strategy,
            profile,
            assumptions,
            theme_labels=[item["theme"] for item in themes],
            promoted_skills=[item["skill_name"] for item in promoted],
        )
        experience_guidance = _build_experience_guidance(profile, options)

        unsupported_tech = [
            item["label"]
            for item in jd_priorities
            if item["kind"] == "technology"
            and item["candidate_support"] == "unsupported"
        ]
        if unsupported_tech:
            assumptions.append(
                "Unsupported employer technology priorities (not used as summary "
                "themes or promoted skills): " + ", ".join(unsupported_tech) + "."
            )

        insufficient = not jd_priorities and not projects and not promoted
        if insufficient:
            assumptions.append(
                "Job analysis and strategy provided insufficient signals for "
                "JD priorities, project emphasis, and skill promotion."
            )

        if options.override_material_benefit:
            assumptions.append(
                "Material-benefit gate was overridden by the caller; "
                "tailoring proceeds despite tier/next-action signals."
            )

        return {
            "application_tier": strategy.application_tier,
            "pursuit_posture": strategy.pursuit_posture,
            "jd_priorities": jd_priorities,
            "projects_to_emphasise": projects,
            "skills_to_promote": promoted,
            "skills_not_emphasised": not_emphasised,
            "summary_themes": themes,
            "experience_guidance": experience_guidance,
            "assumptions": assumptions,
            "owner_review_recommended": True,
            "insufficient_evidence": insufficient,
            "material_benefit_override": options.override_material_benefit,
        }


def _norm(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.casefold()))


def _profile_capabilities(profile: CareerProfile) -> list[str]:
    """Capabilities that may back CV emphasis.

    Uses skills and portfolio project technologies only. Experience-line
    technologies (especially extended history such as Ruby on Rails) must not
    invent summary themes for AI Engineering applications.
    """
    names: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        key = name.casefold()
        if key in seen:
            return
        seen.add(key)
        names.append(name)

    for skill in profile.skills.technical:
        _add(skill.name)
    for skill in profile.skills.domain:
        _add(skill.name)
    for skill in profile.skills.soft:
        _add(skill.name)
    for project in profile.projects:
        for tech in project.technologies:
            _add(tech)
    _add(profile.identity.target_role)
    return names


def _direct_match(left: str, right: str) -> bool:
    """Exact or token-set match — never raw character substring.

    ``Java`` must not match ``JavaScript``; ``sql`` must not match
    ``postgresql``. ``openai`` may match ``openai apis`` via tech-extension
    tokens. ``automation`` must not match ``test automation``.
    """
    a = _norm(left)
    b = _norm(right)
    if not a or not b:
        return False
    if a == b:
        return True
    a_tokens = a.split()
    b_tokens = b.split()
    if len(a_tokens) <= len(b_tokens):
        return _compatible_token_subset(a_tokens, b_tokens)
    return _compatible_token_subset(b_tokens, a_tokens)


def _compatible_token_subset(shorter: list[str], longer: list[str]) -> bool:
    """True when shorter tokens are a compatible subset of longer tokens."""
    if not shorter or not set(shorter) <= set(longer):
        return False
    if len(shorter) >= 2:
        return True
    remainder = [token for token in longer if token not in shorter]
    return bool(remainder) and all(
        token in _TECH_EXTENSION_TOKENS for token in remainder
    )


def _related_match(left: str, right: str) -> bool:
    """True when both labels belong to the same related-capability group.

    Membership is exact on normalised phrases only. Substring checks are
    intentionally avoided so short tokens like ``ai`` do not match inside
    unrelated words (e.g. ``rails``, ``javascript``).
    """
    a = _norm(left)
    b = _norm(right)
    if not a or not b or a == b:
        return False
    for group in _RELATED_CAPABILITY_GROUPS:
        if a in group and b in group:
            return True
    return False


def _classify_against_profile(
    label: str,
    profile_caps: list[str],
) -> tuple[CandidateSupport, str | None]:
    for cap in profile_caps:
        if _direct_match(label, cap):
            return "supported", cap
    for cap in profile_caps:
        if _related_match(label, cap):
            return "related", cap
    return "unsupported", None


def _build_jd_priorities(
    job: JobAnalysis,
    profile: CareerProfile,
    profile_caps: list[str],
) -> list[dict[str, Any]]:
    priorities: list[dict[str, Any]] = []

    def _add_tech(index: int, tech: TechnologyRequirement, level_label: str) -> None:
        if len(priorities) >= _MAX_JD_PRIORITIES:
            return
        support, related_cap = _classify_against_profile(tech.name, profile_caps)
        rationale = (
            f"{tech.name} is listed as {level_label} in the job analysis "
            f"(employer priority; candidate_support={support})."
        )
        priorities.append(
            {
                "rank": len(priorities) + 1,
                "label": tech.name,
                "kind": "technology",
                "rationale": rationale,
                "candidate_support": support,
                "related_profile_capability": related_cap,
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "technology",
                            "item_index": index,
                            "name": tech.name,
                            "excerpt": tech.evidence[0].excerpt if tech.evidence else None,
                        },
                    }
                ],
            }
        )

    for index, tech in enumerate(job.technologies):
        if tech.level == "required":
            _add_tech(index, tech, "required")

    for index, tech in enumerate(job.technologies):
        if tech.level == "preferred":
            _add_tech(index, tech, "preferred")

    for index, tech in enumerate(job.technologies):
        if tech.level == "unspecified":
            _add_tech(index, tech, "unspecified")

    if job.role_family.family not in {"unknown", "other"} and len(priorities) < _MAX_JD_PRIORITIES:
        family = job.role_family.family.replace("_", " ")
        label = family.title()
        support, related_cap = _classify_against_profile(label, profile_caps)
        priorities.append(
            {
                "rank": len(priorities) + 1,
                "label": label,
                "kind": "role_theme",
                "rationale": (
                    f"Role family '{job.role_family.family}' is an employer "
                    f"positioning signal (candidate_support={support})."
                ),
                "candidate_support": support,
                "related_profile_capability": related_cap,
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "role_family",
                            "name": job.role_family.family,
                            "excerpt": (
                                job.role_family.evidence[0].excerpt
                                if job.role_family.evidence
                                else None
                            ),
                        },
                    }
                ],
            }
        )

    for index, responsibility in enumerate(job.responsibilities):
        if len(priorities) >= _MAX_JD_PRIORITIES:
            break
        label = _responsibility_label(responsibility.description)
        # Responsibilities are employer asks; do not treat as candidate-supported
        # themes unless a direct/related capability phrase matches.
        support, related_cap = _classify_against_profile(label, profile_caps)
        priorities.append(
            {
                "rank": len(priorities) + 1,
                "label": label,
                "kind": "responsibility",
                "rationale": (
                    "Responsibility appears in the job analysis as an employer "
                    f"priority (candidate_support={support})."
                ),
                "candidate_support": support,
                "related_profile_capability": related_cap,
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "responsibility",
                            "item_index": index,
                            "excerpt": (
                                responsibility.evidence[0].excerpt
                                if responsibility.evidence
                                else responsibility.description
                            ),
                        },
                    }
                ],
            }
        )

    return priorities


def _responsibility_label(description: str) -> str:
    words = [token for token in _TOKEN_RE.findall(description.casefold()) if len(token) > 2]
    if not words:
        return description[:80]
    return " ".join(words[:6]).title()


def _build_projects(
    strategy: ApplicationStrategy,
    profile: CareerProfile,
    assumptions: list[str],
    *,
    theme_labels: list[str] | None = None,
    promoted_skills: list[str] | None = None,
) -> list[dict[str, Any]]:
    from career_intelligence.cv_generation.content_selection import score_text

    profile_by_id = {project.id: project for project in profile.projects}
    projects: list[dict[str, Any]] = []

    if not strategy.portfolio_emphasis:
        assumptions.append(
            "ApplicationStrategy.portfolio_emphasis is empty; no projects were "
            "emphasised by the Tailoring Plan."
        )
        return projects

    # Weight themes and promoted skills above raw JD technology labels so a
    # single shared API skill does not outrank core AI portfolio evidence.
    primary_hints = list(theme_labels or []) + list(promoted_skills or [])
    secondary_hints = [tech.name for tech in strategy.job_analysis.technologies]
    secondary_hints.append(
        strategy.job_analysis.role_family.family.replace("_", " ")
    )

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for source_rank, emphasis in enumerate(strategy.portfolio_emphasis):
        if emphasis.project_id not in profile_by_id:
            assumptions.append(
                f"Skipped portfolio emphasis project_id '{emphasis.project_id}' "
                "because it is absent from the career profile."
            )
            continue
        project = profile_by_id[emphasis.project_id]
        blob = " ".join(
            [
                project.name,
                project.summary,
                " ".join(project.technologies),
                " ".join(project.outcomes),
                " ".join(project.demonstrates),
            ]
        )
        relevance = (3 * score_text(blob, primary_hints)) + score_text(
            blob, secondary_hints
        )
        family = strategy.job_analysis.role_family.family
        if family in {"ai_engineering", "ai_adjacent"}:
            relevance += 4 * score_text(blob, list(_AI_PROJECT_CAPABILITY_HINTS))
        ranked.append(
            (
                -relevance,
                source_rank,
                {
                    "rank": 0,
                    "project_id": emphasis.project_id,
                    "rationale": emphasis.summary,
                    "evidence": [
                        {
                            "origin": "application_strategy",
                            "portfolio_project_id": emphasis.project_id,
                            "excerpt": emphasis.summary,
                        }
                    ],
                },
            )
        )

    ranked.sort(key=lambda row: (row[0], row[1]))
    for index, (_score, _source_rank, item) in enumerate(ranked, start=1):
        item["rank"] = index
        projects.append(item)

    if ranked and ranked[0][1] != 0:
        assumptions.append(
            "Portfolio project order was re-ranked within ApplicationStrategy "
            "emphasis by overlap with summary themes, promoted skills, AI "
            "capability signals, and job signals."
        )

    # Ensure the Career Intelligence Copilot project can surface for AI-family
    # roles when strategy emphasis omitted it (factual portfolio evidence).
    # Profile appends must follow all ApplicationStrategy emphasis projects
    # (plan_refs); never interleave. Drop weaker non-AI emphasis entries so CIC
    # is not trapped below pure commercial/rules evidence.
    #
    # Known non-blocking limitation (Slice 1 freeze, 2026-08-13): this prune
    # compares `_AI_PROJECT_CAPABILITY_HINTS` overlap, not distinct-claim cover.
    # An AI system that scores below CIC (e.g. Operational Intelligence Copilot)
    # can be omitted even when strategy ranked it first. Owner accepted this as
    # PASS / MINOR EDIT — do not treat it as a freeze defect, special-case
    # Repurpose, or expand project taxonomy to force a third project.
    cic_id = "career-intelligence-copilot"
    included = {item["project_id"] for item in projects}
    family = strategy.job_analysis.role_family.family
    if (
        family in {"ai_engineering", "ai_adjacent"}
        and cic_id in profile_by_id
        and cic_id not in included
    ):
        cic_project = profile_by_id[cic_id]
        cic_blob = " ".join(
            [
                cic_project.name,
                cic_project.summary,
                " ".join(cic_project.technologies),
                " ".join(cic_project.outcomes),
                " ".join(cic_project.demonstrates),
            ]
        )
        cic_ai = score_text(cic_blob, list(_AI_PROJECT_CAPABILITY_HINTS))
        retained: list[dict[str, Any]] = []
        for item in projects:
            existing = profile_by_id.get(item["project_id"])
            if existing is None:
                retained.append(item)
                continue
            existing_blob = " ".join(
                [
                    existing.name,
                    existing.summary,
                    " ".join(existing.technologies),
                    " ".join(existing.outcomes),
                    " ".join(existing.demonstrates),
                ]
            )
            existing_ai = score_text(existing_blob, list(_AI_PROJECT_CAPABILITY_HINTS))
            if existing_ai >= cic_ai:
                retained.append(item)
        if not retained and projects:
            retained = [projects[0]]
        projects = retained
        projects.append(
            {
                "rank": 0,
                "project_id": cic_id,
                "rationale": (
                    "Career Intelligence Copilot added as Career Profile portfolio "
                    "evidence of AI Engineering methodology and decision-support "
                    f"systems for role family '{family}'."
                ),
                "evidence": [
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "project",
                            "ref": f"project:{cic_id}",
                        },
                    }
                ],
            }
        )
        assumptions.append(
            "Included Career Intelligence Copilot from the Career Profile because "
            "ApplicationStrategy portfolio emphasis omitted it for an AI-family role."
        )
        if len(retained) < len(ranked):
            assumptions.append(
                "Deferred lower-AI-signal portfolio emphasis projects so Career "
                "Intelligence Copilot could surface for this AI-family role."
            )
        for index, item in enumerate(projects, start=1):
            item["rank"] = index

    return projects


def _iter_profile_skills(
    profile: CareerProfile,
) -> list[tuple[str, Skill]]:
    items: list[tuple[str, Skill]] = []
    for skill in profile.skills.technical:
        items.append(("technical", skill))
    for skill in profile.skills.domain:
        items.append(("domain", skill))
    for skill in profile.skills.soft:
        items.append(("soft", skill))
    return items


def _capability_is_foundational(profile: CareerProfile, name: str) -> bool:
    from career_intelligence.profile import skill_prominence_band

    for _category, skill in _iter_profile_skills(profile):
        if skill.name.casefold() == name.casefold():
            return skill_prominence_band(profile, skill) == "foundational"
    return False


def _build_skills(
    job: JobAnalysis,
    profile: CareerProfile,
    profile_caps: list[str],
    assumptions: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Promote only Career Profile skills that support a JD technology.

    Among matches, stronger profile evidence (employment / portfolio) ranks above
    professional-development-only capabilities such as studied-but-not-shipped tools.
    """
    from career_intelligence.profile import (
        evidence_strength_rank,
        skill_prominence_band,
        strongest_evidence_kind,
    )

    profile_skills = _iter_profile_skills(profile)
    candidates: list[dict[str, Any]] = []
    promoted_names: set[str] = set()
    _LEVEL_RANK = {"required": 0, "preferred": 1, "unspecified": 2}

    def _try_promote(
        skill_category: str,
        skill: Skill,
        tech_index: int,
        tech: TechnologyRequirement,
        support: CandidateSupport,
    ) -> None:
        key = skill.name.casefold()
        if key in promoted_names:
            return
        if support == "unsupported":
            return
        if support == "supported" and not _direct_match(skill.name, tech.name):
            return
        if support == "related" and not _related_match(skill.name, tech.name):
            return
        if skill_prominence_band(profile, skill) == "foundational":
            return

        promoted_names.add(key)
        strength = strongest_evidence_kind(profile, skill)
        if support == "supported":
            rationale = (
                f"{skill.name} promoted because it is both a key JD "
                f"requirement ({tech.name}, {tech.level}) and evidenced in the "
                f"Career Profile via {strength.replace('_', ' ')}."
            )
        else:
            rationale = (
                f"{skill.name} promoted because it is evidenced in the Career "
                f"Profile via {strength.replace('_', ' ')} and supports the "
                f"employer's '{tech.name}' requirement ({tech.level})."
            )
        candidates.append(
            {
                "skill_name": skill.name,
                "category": skill_category,
                "rationale": rationale,
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "technology",
                            "item_index": tech_index,
                            "name": tech.name,
                            "excerpt": tech.evidence[0].excerpt if tech.evidence else None,
                        },
                    },
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "skill",
                            "ref": f"skill:{skill.name}",
                        },
                    },
                ],
                "_jd_level_rank": _LEVEL_RANK.get(tech.level, 9),
                "_evidence_rank": evidence_strength_rank(strength),
                "_strength": strength,
            }
        )

    for level in ("required", "preferred", "unspecified"):
        for tech_index, tech in enumerate(job.technologies):
            if tech.level != level:
                continue
            support, _ = _classify_against_profile(tech.name, profile_caps)
            if support == "unsupported":
                continue
            for category, skill in profile_skills:
                if support == "supported" and _direct_match(skill.name, tech.name):
                    _try_promote(category, skill, tech_index, tech, "supported")
                elif support == "related" and _related_match(skill.name, tech.name):
                    _try_promote(category, skill, tech_index, tech, "related")

    candidates.sort(
        key=lambda item: (
            item["_jd_level_rank"],
            item["_evidence_rank"],
            item["skill_name"].casefold(),
        )
    )
    promoted: list[dict[str, Any]] = []
    for item in candidates[:_MAX_PROMOTED_SKILLS]:
        strength = item.pop("_strength")
        item.pop("_jd_level_rank")
        item.pop("_evidence_rank")
        item["rank"] = len(promoted) + 1
        if strength == "professional_development":
            item["rationale"] += (
                " Professional-development evidence is retained as truthful "
                "but ranked below employment and portfolio demonstration."
            )
        promoted.append(item)

    not_emphasised: list[dict[str, Any]] = []
    for category, skill in profile_skills:
        if skill.name.casefold() in promoted_names:
            continue
        not_emphasised.append(
            {
                "skill_name": skill.name,
                "category": category,
                "rationale": (
                    f"{skill.name} remains on the CV but is not emphasised "
                    "because it does not support a candidate-backed JD technology."
                ),
            }
        )

    if not promoted and profile_skills:
        assumptions.append(
            "No Career Profile skills were both JD-relevant and evidence-backed; "
            "no skills were promoted."
        )

    return promoted, not_emphasised


def _build_summary_themes(
    job: JobAnalysis,
    jd_priorities: list[dict[str, Any]],
    profile: CareerProfile,
    assumptions: list[str],
) -> list[dict[str, Any]]:
    """Themes require JD relevance AND candidate evidence (supported/related).

    Candidate-supported themes are ordered by evidence strength so employment /
    portfolio demonstration outranks professional-development-only capabilities.
    """
    from career_intelligence.profile import (
        evidence_strength_rank,
        strongest_evidence_kind_for_capability,
    )

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    _SUPPORT_RANK = {"supported": 0, "related": 1}

    def _queue_theme(
        theme: str,
        rationale: str,
        evidence: list[dict[str, Any]],
        *,
        support: CandidateSupport,
        jd_order: int,
    ) -> None:
        key = theme.casefold()
        if key in seen:
            return
        if _capability_is_foundational(profile, theme):
            return
        seen.add(key)
        strength = strongest_evidence_kind_for_capability(profile, theme)
        note = rationale
        if strength == "professional_development":
            note += (
                " Professional-development evidence is retained as truthful "
                "but ranked below employment and portfolio demonstration."
            )
        candidates.append(
            {
                "theme": theme,
                "rationale": note,
                "evidence": list(evidence),
                "_support_rank": _SUPPORT_RANK.get(support, 9),
                "_evidence_rank": evidence_strength_rank(strength),
                "_jd_order": jd_order,
            }
        )

    for jd_order, priority in enumerate(jd_priorities):
        support = priority["candidate_support"]
        if support == "unsupported":
            continue
        if priority["kind"] == "responsibility" and support != "supported":
            continue

        if support == "supported":
            theme = str(priority["related_profile_capability"] or priority["label"])
            rationale = (
                f"Summary theme '{theme}' is both a JD priority "
                f"({priority['label']}) and evidenced in the Career Profile."
            )
            evidence = list(priority["evidence"])
            evidence.append(
                {
                    "origin": "career_profile",
                    "profile_evidence": {
                        "source": "skill"
                        if priority["kind"] == "technology"
                        else "identity",
                        "ref": (
                            f"skill:{theme}"
                            if priority["kind"] == "technology"
                            else "identity:target_role"
                        ),
                    },
                }
            )
            skill_names = {
                s.name.casefold()
                for s in (
                    *profile.skills.technical,
                    *profile.skills.domain,
                    *profile.skills.soft,
                )
            }
            if priority["kind"] == "technology" and theme.casefold() not in skill_names:
                evidence[-1] = {
                    "origin": "career_profile",
                    "profile_evidence": {
                        "source": "project",
                        "ref": f"project:{profile.projects[0].id}",
                        "excerpt": theme,
                    },
                }
            _queue_theme(
                theme,
                rationale,
                evidence,
                support="supported",
                jd_order=jd_order,
            )
        elif support == "related":
            related = priority.get("related_profile_capability")
            if not related:
                continue
            rationale = (
                f"Summary theme '{related}' is evidenced in the Career Profile "
                f"and supports employer priority '{priority['label']}' "
                "(related capability; not an unsupported claim)."
            )
            evidence = list(priority["evidence"])
            skill_names = {
                s.name.casefold()
                for s in (
                    *profile.skills.technical,
                    *profile.skills.domain,
                    *profile.skills.soft,
                )
            }
            if related.casefold() in skill_names:
                evidence.append(
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "skill",
                            "ref": f"skill:{related}",
                        },
                    }
                )
            else:
                evidence.append(
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "identity",
                            "ref": "identity:target_role",
                            "excerpt": related,
                        },
                    }
                )
            _queue_theme(
                str(related),
                rationale,
                evidence,
                support="related",
                jd_order=jd_order,
            )

    if not candidates and job.role_family.family not in {"unknown", "other"}:
        family = job.role_family.family.replace("_", " ").title()
        if _direct_match(profile.identity.target_role, family) or _related_match(
            profile.identity.target_role, family
        ):
            _queue_theme(
                profile.identity.target_role,
                (
                    f"Summary theme reflects target role "
                    f"'{profile.identity.target_role}' aligned to role family "
                    f"'{job.role_family.family}'."
                ),
                [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "role_family",
                            "name": job.role_family.family,
                        },
                    },
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "identity",
                            "ref": "identity:target_role",
                        },
                    },
                ],
                support="related",
                jd_order=10_000,
            )

    candidates.sort(
        key=lambda item: (
            item["_support_rank"],
            item["_evidence_rank"],
            item["_jd_order"],
            item["theme"].casefold(),
        )
    )
    themes: list[dict[str, Any]] = []
    for item in candidates[:_MAX_SUMMARY_THEMES]:
        item.pop("_support_rank")
        item.pop("_evidence_rank")
        item.pop("_jd_order")
        item["rank"] = len(themes) + 1
        themes.append(item)

    if not themes:
        assumptions.append(
            "No candidate-supported summary themes could be derived; Phase C "
            "must not invent unsupported technology themes."
        )

    return themes


def _ensure_role_family_skill_anchors(
    job: JobAnalysis,
    profile: CareerProfile,
    promoted: list[dict[str, Any]],
    not_emphasised: list[dict[str, Any]],
    assumptions: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Seed truthful profile anchors when JD overlap yields sparse promotions."""
    anchors = _ROLE_FAMILY_PROFILE_ANCHORS.get(job.role_family.family)
    if not anchors:
        return promoted, not_emphasised
    if len(promoted) >= _MIN_PROMOTED_SKILLS_FOR_AI_FAMILY:
        return promoted, not_emphasised

    profile_skills = {
        skill.name.casefold(): (category, skill)
        for category, skill in _iter_profile_skills(profile)
    }
    promoted_names = {item["skill_name"].casefold() for item in promoted}
    added: list[str] = []

    for anchor in anchors:
        if len(promoted) >= _MAX_PROMOTED_SKILLS:
            break
        if len(promoted) >= _MIN_PROMOTED_SKILLS_FOR_AI_FAMILY:
            break
        key = anchor.casefold()
        if key in promoted_names:
            continue
        match = profile_skills.get(key)
        if match is None:
            continue
        category, skill = match
        if _capability_is_foundational(profile, skill.name):
            continue
        promoted_names.add(key)
        added.append(skill.name)
        promoted.append(
            {
                "rank": len(promoted) + 1,
                "skill_name": skill.name,
                "category": category,
                "rationale": (
                    f"{skill.name} promoted as a Career Profile capability "
                    f"aligned to role family '{job.role_family.family}' when "
                    "JD technology overlap was sparse."
                ),
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "role_family",
                            "name": job.role_family.family,
                        },
                    },
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "skill",
                            "ref": f"skill:{skill.name}",
                        },
                    },
                ],
            }
        )

    if added:
        assumptions.append(
            "Role-family profile anchors added to promoted skills because JD "
            "technology overlap was sparse: " + ", ".join(added) + "."
        )
        not_emphasised = [
            item
            for item in not_emphasised
            if item["skill_name"].casefold() not in promoted_names
        ]
        for index, item in enumerate(promoted, start=1):
            item["rank"] = index

    return promoted, not_emphasised


def _ensure_role_family_theme_anchors(
    job: JobAnalysis,
    profile: CareerProfile,
    themes: list[dict[str, Any]],
    promoted: list[dict[str, Any]],
    assumptions: list[str],
) -> list[dict[str, Any]]:
    """Ensure summary themes reflect role-family anchors when themes are weak."""
    anchors = _ROLE_FAMILY_PROFILE_ANCHORS.get(job.role_family.family)
    if not anchors:
        return themes

    theme_keys = {item["theme"].casefold() for item in themes}
    # Treat lone weak themes (e.g. historical QA) as needing reinforcement.
    needs_seed = len(themes) < 2 or (
        len(themes) == 1
        and themes[0]["theme"].casefold()
        in {"test automation", "software quality assurance"}
    )
    if not needs_seed:
        return themes

    # Prefer promoted skill names, then configured anchors present on the profile.
    profile_caps = {cap.casefold() for cap in _profile_capabilities(profile)}
    candidates = [item["skill_name"] for item in promoted]
    for anchor in anchors:
        if anchor not in candidates:
            candidates.append(anchor)

    added: list[str] = []
    for label in candidates:
        if len(themes) >= _MAX_SUMMARY_THEMES:
            break
        key = label.casefold()
        if key in theme_keys:
            continue
        if key not in profile_caps:
            continue
        if _capability_is_foundational(profile, label):
            continue
        # Drop a lone weak theme so anchors lead the summary.
        if (
            len(themes) == 1
            and themes[0]["theme"].casefold()
            in {"test automation", "software quality assurance"}
        ):
            removed = themes.pop(0)
            theme_keys.discard(removed["theme"].casefold())
            assumptions.append(
                f"Replaced weak summary theme '{removed['theme']}' with "
                "role-family profile anchors."
            )
        theme_keys.add(key)
        added.append(label)
        themes.append(
            {
                "rank": len(themes) + 1,
                "theme": label,
                "rationale": (
                    f"Summary theme '{label}' is evidenced in the Career Profile "
                    f"and reinforces role family '{job.role_family.family}'."
                ),
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "role_family",
                            "name": job.role_family.family,
                        },
                    },
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "skill"
                            if any(
                                s.name.casefold() == key
                                for s in (
                                    *profile.skills.technical,
                                    *profile.skills.domain,
                                    *profile.skills.soft,
                                )
                            )
                            else "identity",
                            "ref": (
                                f"skill:{label}"
                                if any(
                                    s.name.casefold() == key
                                    for s in (
                                        *profile.skills.technical,
                                        *profile.skills.domain,
                                        *profile.skills.soft,
                                    )
                                )
                                else "identity:target_role"
                            ),
                        },
                    },
                ],
            }
        )
        if len(themes) >= 3:
            break

    if added:
        assumptions.append(
            "Role-family summary themes reinforced with profile anchors: "
            + ", ".join(added)
            + "."
        )
        for index, item in enumerate(themes, start=1):
            item["rank"] = index

    return themes


def _build_experience_guidance(
    profile: CareerProfile,
    options: TailoringOptions,
) -> dict[str, Any]:
    included, excluded = partition_experience_ids(
        profile,
        include_extended_history=options.include_extended_history,
    )
    if options.include_extended_history:
        kind = "include_extended_history"
        rationale = (
            "Caller opted in to include extended (pre-Master-CV) experience "
            "history on the tailored CV."
        )
    else:
        kind = "master_cv_only"
        rationale = (
            "Default Master-CV-aligned scope: extended pre-nbn history is "
            "excluded unless the caller opts in."
        )
    return {
        "kind": kind,
        "rationale": rationale,
        "included_experience_ids": included,
        "excluded_experience_ids": excluded,
    }
