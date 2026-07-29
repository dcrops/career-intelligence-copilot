"""Deterministic CoverLetterPlan planner for FR-007 Phase A.

Package-private production path. Returns an untrusted payload; callers must
obtain trusted output through CoverLetterPlanService.

Owns composition decisions only. Does not generate final letter prose.
"""

from __future__ import annotations

import re

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.profile.models import CareerProfile, Project

from .options import CoverLetterPlanOptions
from .planner import CoverLetterPlanPayload
from .project_selection import select_projects_for_letter

_MAX_EVIDENCE = 3
_MAX_PROJECTS = 3


class DeterministicCoverLetterPlanner:
    """Build a CoverLetterPlan payload from ApplicationStrategy + Career Profile."""

    def plan(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        options: CoverLetterPlanOptions,
    ) -> CoverLetterPlanPayload:
        job = strategy.job_analysis
        company = (job.posting.company or "").strip() or "the hiring organisation"
        role_title = (job.posting.title or "").strip() or profile.identity.target_role

        assumptions: list[str] = []
        if options.override_material_benefit:
            assumptions.append(
                "Material-benefit gate was overridden by the caller; cover letter "
                "planning proceeds despite tier/next-action signals."
            )

        company_alignment = _build_company_alignment(strategy, company)
        role_motivation = _build_role_motivation(strategy, role_title)
        relevant_evidence = _build_relevant_evidence(profile, strategy)
        strongest_projects = _build_strongest_projects(profile, strategy)
        closing_strategy = _build_closing_strategy(strategy, company, role_title)

        insufficient = (
            len(relevant_evidence) == 0
            and len(strongest_projects) == 0
            and not (profile.identity.summary or "").strip()
        )
        if insufficient:
            assumptions.append(
                "Insufficient Career Profile evidence for a strong cover letter; "
                "plan marks insufficient_evidence=True."
            )
            # Fail soft with minimal identity-backed evidence so validation can still
            # produce a reviewable plan when identity summary exists.
            relevant_evidence = [
                {
                    "kind": "capability",
                    "claim": (
                        f"{profile.identity.target_role} with evidence-backed "
                        "portfolio delivery."
                    ),
                    "evidence": [
                        {
                            "origin": "career_profile",
                            "profile_source": "identity",
                            "excerpt": profile.identity.target_role,
                        }
                    ],
                }
            ]

        return {
            "application_tier": strategy.application_tier,
            "pursuit_posture": strategy.pursuit_posture,
            "company_alignment": company_alignment,
            "role_motivation": role_motivation,
            "relevant_evidence": relevant_evidence[:_MAX_EVIDENCE],
            "strongest_projects": strongest_projects[:_MAX_PROJECTS],
            "closing_strategy": closing_strategy,
            "assumptions": assumptions,
            "insufficient_evidence": insufficient,
            "material_benefit_override": options.override_material_benefit,
        }


def _build_company_alignment(
    strategy: ApplicationStrategy,
    company: str,
) -> dict[str, object]:
    job = strategy.job_analysis
    hook, evidence = _company_hook(strategy, company)
    return {
        "company": company,
        "alignment_hook": hook,
        "evidence": evidence,
    }


def _company_hook(
    strategy: ApplicationStrategy,
    company: str,
) -> tuple[str, list[dict[str, object]]]:
    """Return a grounded attraction signal suitable for letter prose."""
    job = strategy.job_analysis
    role_title = (job.posting.title or "").strip()
    family = job.role_family.family if job.role_family else "unknown"

    if job.role_family and job.role_family.evidence:
        excerpt = _scrub_hook_marketing(job.role_family.evidence[0].excerpt.strip())
        if excerpt and _is_usable_attraction_hook(
            excerpt, company=company, role_title=role_title
        ):
            return (
                excerpt.rstrip("."),
                [
                    {
                        "origin": "job_analysis",
                        "job_source": "role_family",
                        "excerpt": job.role_family.evidence[0].excerpt.strip(),
                    }
                ],
            )

    for index, responsibility in enumerate(job.responsibilities[:3]):
        description = _scrub_hook_marketing(responsibility.description.strip())
        if description and _is_usable_attraction_hook(
            description, company=company, role_title=role_title
        ):
            return (
                _short_theme(description, limit=120),
                [
                    {
                        "origin": "job_analysis",
                        "job_source": "responsibility",
                        "job_index": index,
                        "excerpt": responsibility.description.strip(),
                    }
                ],
            )

    alignment_reasons = [
        reason for reason in strategy.reasons if reason.kind == "alignment"
    ]
    if alignment_reasons:
        summary = alignment_reasons[0].summary.strip()
        return (
            _short_theme(summary, limit=120),
            [
                {
                    "origin": "application_strategy",
                    "excerpt": summary,
                }
            ],
        )

    family_label = family.replace("_", " ") if family != "unknown" else "AI engineering"
    return (
        f"AI Engineering work in {family_label}",
        [
            {
                "origin": "job_analysis",
                "job_source": "role_family",
                "excerpt": family_label,
            }
        ],
    )


def _is_usable_attraction_hook(
    text: str,
    *,
    company: str,
    role_title: str,
) -> bool:
    """Reject title-only or company-blurb hooks (marketing already scrubbed)."""
    cleaned = " ".join(text.split()).strip().rstrip(".")
    if len(cleaned) < 24:
        return False
    folded = cleaned.casefold()
    if role_title and folded == role_title.casefold():
        return False
    if company and folded == company.casefold():
        return False
    if company and folded.startswith(f"{company.casefold()} is "):
        return False
    if re.match(r"^[A-Z][\w .&'-]{1,60}\s+is an?\b", cleaned):
        return False
    return True


def _scrub_hook_marketing(text: str) -> str:
    """Remove slogan language while preserving domain/engineering substance."""
    cleaned = " ".join(text.split()).strip()
    for fluff in (
        "shaping the future of",
        "shaping the future",
        "the future of",
        "cutting-edge",
        "world-class",
        "best-in-class",
        "next-generation of",
        "revolutionising",
        "revolutionizing",
    ):
        cleaned = re.sub(re.escape(fluff), "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;.-")
    cleaned = re.sub(
        r"\bAI systems\s+fintech\b",
        "AI systems for fintech",
        cleaned,
        flags=re.I,
    )
    return cleaned.strip()


def _build_role_motivation(
    strategy: ApplicationStrategy,
    role_title: str,
) -> dict[str, object]:
    """Store compact engineering themes for the renderer — not 'brief emphasises' prose."""
    job = strategy.job_analysis
    themes: list[str] = []
    evidence: list[dict[str, object]] = []

    for index, responsibility in enumerate(job.responsibilities[:3]):
        text = responsibility.description.strip()
        if not text:
            continue
        themes.append(_short_theme(text))
        evidence.append(
            {
                "origin": "job_analysis",
                "job_source": "responsibility",
                "job_index": index,
                "excerpt": text,
            }
        )

    tech_names = [item.name for item in job.technologies[:4] if item.name.strip()]
    if tech_names:
        evidence.append(
            {
                "origin": "job_analysis",
                "job_source": "technology",
                "job_index": 0,
                "excerpt": ", ".join(tech_names),
            }
        )

    # Single clean theme — renderer embeds this; avoid joined JD dumps.
    if themes:
        motivation = themes[0]
    elif tech_names:
        motivation = _oxford_join(tech_names[:3])
    else:
        motivation = "production-minded AI Engineering delivery"
        evidence.append(
            {
                "origin": "application_strategy",
                "excerpt": strategy.summary,
            }
        )

    return {
        "role_title": role_title,
        "motivation": motivation,
        "evidence": evidence[:3]
        or [
            {
                "origin": "application_strategy",
                "excerpt": strategy.summary,
            }
        ],
    }


def _short_theme(text: str, *, limit: int = 90) -> str:
    """Compact JD theme for the plan; renderer turns this into letter prose."""
    cleaned = " ".join(text.split()).strip().rstrip(".")
    # Prefer the main clause before elaborating ", including …" tails.
    including_at = cleaned.casefold().find(", including")
    if including_at > 40:
        cleaned = cleaned[:including_at].rstrip()
    if len(cleaned) > limit:
        cleaned = cleaned[:limit].rsplit(" ", 1)[0].rstrip(",;:") or cleaned[:limit]
    while True:
        lowered = cleaned.casefold()
        stripped = False
        for suffix in (
            " and",
            " or",
            " including the",
            " including",
            " with",
            " for",
            " to",
            " the",
            " a",
            " an",
            " across",
        ):
            if lowered.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].rstrip(",;: ")
                stripped = True
                break
        if not stripped:
            break
    return cleaned



def _build_relevant_evidence(
    profile: CareerProfile,
    strategy: ApplicationStrategy,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    summary = (profile.identity.summary or "").strip()
    if summary:
        # Prefer the commercial years + portfolio span sentences when present.
        claim = _profile_credibility_claim(summary, profile.identity.target_role)
        items.append(
            {
                "kind": "commercial_experience",
                "claim": claim,
                "evidence": [
                    {
                        "origin": "career_profile",
                        "profile_source": "identity",
                        "excerpt": claim[:180],
                    }
                ],
            }
        )

    for highlight in profile.selected_engineering_highlights[:2]:
        text = " ".join(highlight.split()).strip()
        if not text:
            continue
        items.append(
            {
                "kind": "engineering_practice",
                "claim": text,
                "evidence": [
                    {
                        "origin": "career_profile",
                        "profile_source": "identity",
                        "excerpt": text[:180],
                    }
                ],
            }
        )

    if not items and strategy.portfolio_emphasis:
        project_id = strategy.portfolio_emphasis[0].project_id
        project = _project_by_id(profile, project_id)
        if project is not None:
            items.append(
                {
                    "kind": "portfolio_project",
                    "claim": project.summary.strip(),
                    "project_id": project.id,
                    "evidence": [
                        {
                            "origin": "portfolio_match",
                            "portfolio_project_id": project.id,
                            "excerpt": project.summary[:180],
                        }
                    ],
                }
            )
    return items[:_MAX_EVIDENCE]


def _build_strongest_projects(
    profile: CareerProfile,
    strategy: ApplicationStrategy,
) -> list[dict[str, object]]:
    """Select projects by JD/strategy evidence fit, not popularity alone."""
    ranked = select_projects_for_letter(
        profile,
        strategy,
        max_projects=_MAX_PROJECTS,
    )
    projects: list[dict[str, object]] = []
    for rank, item in enumerate(ranked, start=1):
        project = item.project
        emphasis_summary = next(
            (
                entry.summary
                for entry in strategy.portfolio_emphasis
                if entry.project_id == project.id
            ),
            None,
        )
        evidence: list[dict[str, object]] = [
            {
                "origin": "career_profile",
                "profile_source": "project",
                "profile_id": project.id,
                "excerpt": project.summary[:180],
            },
            {
                "origin": "application_strategy",
                "excerpt": item.selection_reason[:180],
            },
        ]
        if emphasis_summary:
            evidence.append(
                {
                    "origin": "application_strategy",
                    "excerpt": emphasis_summary[:180],
                }
            )
        elif item.matched_tags:
            evidence.append(
                {
                    "origin": "portfolio_match",
                    "portfolio_project_id": project.id,
                    "excerpt": ", ".join(item.matched_tags[:5]),
                }
            )
        projects.append(
            {
                "rank": rank,
                "project_id": project.id,
                "project_name": project.name,
                "emphasis": project.summary.strip(),
                "selection_reason": item.selection_reason,
                "business_outcome": item.business_outcome,
                "fit_focus": item.fit_focus,
                "evidence": evidence[:3],
            }
        )
    return projects


def _build_closing_strategy(
    strategy: ApplicationStrategy,
    company: str,
    role_title: str,
) -> dict[str, object]:
    if strategy.pursuit_posture in {"prioritise", "pursue"}:
        approach = "contribution_focus"
        intent = (
            f"Close by offering a concrete discussion of how AI Engineering "
            f"delivery can support {company}'s {role_title} priorities."
        )
    else:
        approach = "conversation_request"
        intent = (
            f"Close by inviting a conversation about the {role_title} role at "
            f"{company}."
        )
    return {
        "approach": approach,
        "intent": intent,
        "evidence": [
            {
                "origin": "application_strategy",
                "excerpt": strategy.pursuit_posture,
            }
        ],
    }


def _profile_credibility_claim(summary: str, target_role: str) -> str:
    lowered = summary.casefold()
    if "3.5 years" in lowered and "data engineering" in lowered:
        return (
            f"{target_role} with 3.5 years of commercial enterprise Data Engineering "
            "experience and an independent AI Engineering portfolio."
        )
    if "data engineering" in lowered:
        first = summary.split(".")[0].strip()
        return first if first else summary[:200]
    first = summary.split(".")[0].strip()
    return first if first else f"{target_role} with evidence-backed AI delivery."


def _project_by_id(profile: CareerProfile, project_id: str) -> Project | None:
    for project in profile.projects:
        if project.id == project_id:
            return project
    return None


def _oxford_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
