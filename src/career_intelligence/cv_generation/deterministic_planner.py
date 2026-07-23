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

CandidateSupport = Literal["supported", "related", "unsupported"]

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
        projects = _build_projects(strategy, profile, assumptions)
        promoted, not_emphasised = _build_skills(
            job, profile, profile_caps, assumptions
        )
        themes = _build_summary_themes(job, jd_priorities, profile, assumptions)
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
    ``postgresql``. ``openai`` may match ``openai apis`` via token subset.
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
        return set(a_tokens) <= set(b_tokens)
    return set(b_tokens) <= set(a_tokens)


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
) -> list[dict[str, Any]]:
    profile_ids = {project.id for project in profile.projects}
    projects: list[dict[str, Any]] = []

    if not strategy.portfolio_emphasis:
        assumptions.append(
            "ApplicationStrategy.portfolio_emphasis is empty; no projects were "
            "emphasised by the Tailoring Plan."
        )
        return projects

    for emphasis in strategy.portfolio_emphasis:
        if emphasis.project_id not in profile_ids:
            assumptions.append(
                f"Skipped portfolio emphasis project_id '{emphasis.project_id}' "
                "because it is absent from the career profile."
            )
            continue
        projects.append(
            {
                "rank": len(projects) + 1,
                "project_id": emphasis.project_id,
                "rationale": emphasis.summary,
                "evidence": [
                    {
                        "origin": "application_strategy",
                        "portfolio_project_id": emphasis.project_id,
                        "excerpt": emphasis.summary,
                    }
                ],
            }
        )
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
