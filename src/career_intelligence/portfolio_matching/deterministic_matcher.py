"""Deterministic portfolio matcher for FR-004.

Package-private production ranking path. Returns an untrusted payload; callers
must obtain trusted output through PortfolioMatchingService.

Calibration (corpus-justified):
- Distinctive technology hits outrank generic stack hits (Python, SQL, REST, …).
- Capability-family overlap ranks alongside technology (RAG, agents, orchestration, …).
- Generic required/preferred hits remain explainable factors but sort after capability
  and distinctive preferred signals so common stack terms cannot dominate ranking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from career_intelligence.job_analysis.models import (
    JobAnalysis,
    Responsibility,
    TechnologyRequirement,
)
from career_intelligence.profile.models import CareerProfile, Project

from .matcher import PortfolioMatchPayload

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Light English filter for responsibility/demonstrates token overlap only.
# Technology matching uses phrase/equality checks and does not apply this set.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "on",
        "or",
        "our",
        "over",
        "that",
        "the",
        "their",
        "this",
        "to",
        "under",
        "use",
        "used",
        "using",
        "we",
        "will",
        "with",
        "you",
    }
)

# Shared baseline stack terms that must not dominate capability-relevant ranking.
# Kept conservative — distinctive AI/platform technologies stay fully weighted.
_GENERIC_TECHNOLOGIES = frozenset(
    {
        "python",
        "sql",
        "t-sql",
        "tsql",
        "rest",
        "rest api",
        "rest apis",
        "api",
        "apis",
        "docker",
        "git",
        "json",
        "http",
        "https",
        "linux",
        "bash",
        "shell",
        "javascript",
        "html",
        "css",
        "excel",
        "yaml",
        "xml",
        "csv",
        "pytest",
        "unittest",
    }
)

# Capability families: phrase/token markers matched in job + project narrative text.
# One shared family between job and project yields one capability_overlap factor.
_CAPABILITY_FAMILIES: dict[str, tuple[str, ...]] = {
    "orchestration": (
        "orchestration",
        "orchestrate",
        "ai orchestration",
    ),
    "workflows_pipelines": (
        "workflow",
        "workflows",
        "application pipeline",
        "application pipelines",
        "autonomous workflow",
        "autonomous workflows",
        "multi-stage",
        "multistage",
        "planning",
    ),
    "agents_reasoning": (
        "agent",
        "agents",
        "agentic",
        "multi-agent",
        "multi agent",
        "reasoning",
        "intent routing",
    ),
    "rag_retrieval": (
        "rag",
        "retrieval",
        "retrieval-augmented",
        "retrieval augmented",
        "embedding",
        "embeddings",
        "grounding",
        "vector",
        "document intelligence",
    ),
    "llm_generative": (
        "llm",
        "llms",
        "generative ai",
        "prompt engineering",
        "openai",
    ),
    "explainability_governance": (
        "explainability",
        "explainable",
        "governance",
        "traceability",
        "traceable",
        "deterministic",
        "audit",
    ),
    "evaluation_llmops": (
        "evaluation",
        "llmops",
        "mlops",
        "telemetry",
        "observability",
        "monitoring",
    ),
    "hitl_review": (
        "human-in-the-loop",
        "human in the loop",
        "hitl",
        "owner review",
        "human review",
    ),
    "production_ai_lifecycle": (
        "production ai",
        "production system",
        "production systems",
        "reliability",
        "incident response",
        "operational intelligence",
    ),
    "document_generation": (
        "document generation",
        "cv generation",
        "cover letter",
        "tailored cv",
    ),
}

_TIE_BREAK_REASON = (
    "equal primary ranking signals; ordered by stable project_id ascending"
)


@dataclass(frozen=True)
class _PrimaryKey:
    distinctive_required_technology: int
    distinctive_preferred_technology: int
    demonstrates_overlap: int
    responsibility_overlap: int
    capability_overlap: int
    generic_required_technology: int
    generic_preferred_technology: int
    unspecified_technology: int


@dataclass
class _ProjectScore:
    project: Project
    distinctive_required_technology: int = 0
    distinctive_preferred_technology: int = 0
    demonstrates_overlap: int = 0
    responsibility_overlap: int = 0
    capability_overlap: int = 0
    generic_required_technology: int = 0
    generic_preferred_technology: int = 0
    unspecified_technology: int = 0
    factors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def required_technology(self) -> int:
        """Total required tech hits (distinctive + generic) for rationales."""
        return (
            self.distinctive_required_technology + self.generic_required_technology
        )

    @property
    def preferred_technology(self) -> int:
        return (
            self.distinctive_preferred_technology + self.generic_preferred_technology
        )

    @property
    def primary_key(self) -> _PrimaryKey:
        return _PrimaryKey(
            distinctive_required_technology=self.distinctive_required_technology,
            distinctive_preferred_technology=self.distinctive_preferred_technology,
            demonstrates_overlap=self.demonstrates_overlap,
            responsibility_overlap=self.responsibility_overlap,
            capability_overlap=self.capability_overlap,
            generic_required_technology=self.generic_required_technology,
            generic_preferred_technology=self.generic_preferred_technology,
            unspecified_technology=self.unspecified_technology,
        )

    @property
    def has_factors(self) -> bool:
        return bool(self.factors)

    def sort_key(self) -> tuple[int, ...]:
        return (
            -self.distinctive_required_technology,
            -self.distinctive_preferred_technology,
            -self.demonstrates_overlap,
            -self.responsibility_overlap,
            -self.capability_overlap,
            -self.generic_required_technology,
            -self.generic_preferred_technology,
            -self.unspecified_technology,
            self.project.id,
        )


class DeterministicMatcher:
    """Rank portfolio projects with deterministic, evidence-backed overlap rules.

    Not exported from the public package API. Inject explicitly into
    PortfolioMatchingService.
    """

    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatchPayload:
        if not _has_usable_signals(job_analysis):
            return {
                "ranked_projects": [],
                "unranked_project_ids": [project.id for project in profile.projects],
                "summary": (
                    "Insufficient job evidence for portfolio ranking: the analysis "
                    "has no usable technologies or responsibilities."
                ),
                "insufficient_evidence": True,
            }

        job_capabilities = _job_capability_families(job_analysis)
        scores = [
            _score_project(project, job_analysis, job_capabilities)
            for project in profile.projects
        ]
        ranked_scores = sorted(
            (score for score in scores if score.has_factors),
            key=lambda score: score.sort_key(),
        )
        unranked_ids = sorted(
            score.project.id for score in scores if not score.has_factors
        )

        ranked_projects = _build_ranked_projects(ranked_scores)
        return {
            "ranked_projects": ranked_projects,
            "unranked_project_ids": unranked_ids,
            "summary": _build_summary(ranked_projects, unranked_ids),
            "insufficient_evidence": False,
        }


def _has_usable_signals(job_analysis: JobAnalysis) -> bool:
    return bool(job_analysis.technologies) or bool(job_analysis.responsibilities)


def _normalise_tech_name(name: str) -> str:
    return " ".join(name.casefold().strip().split())


def _is_generic_technology(name: str) -> bool:
    return _normalise_tech_name(name) in _GENERIC_TECHNOLOGIES


def _score_project(
    project: Project,
    job_analysis: JobAnalysis,
    job_capabilities: dict[str, dict[str, Any]],
) -> _ProjectScore:
    score = _ProjectScore(project=project)
    searchable = _project_searchable_text(project)
    demonstrates_tokens = _significant_tokens(" ".join(project.demonstrates))
    responsibility_field_tokens = _significant_tokens(
        " ".join(
            [
                project.summary,
                *project.outcomes,
                *project.technologies,
            ]
        )
    )
    project_capability_text = " ".join(
        [
            *project.demonstrates,
            project.summary,
        ]
    )

    for index, technology in enumerate(job_analysis.technologies):
        matched_excerpt = _technology_match_excerpt(technology.name, project, searchable)
        if matched_excerpt is None:
            continue
        kind = _technology_factor_kind(technology.level)
        generic = _is_generic_technology(technology.name)
        if kind == "required_technology":
            if generic:
                score.generic_required_technology += 1
            else:
                score.distinctive_required_technology += 1
        elif kind == "preferred_technology":
            if generic:
                score.generic_preferred_technology += 1
            else:
                score.distinctive_preferred_technology += 1
        else:
            score.unspecified_technology += 1
        score.factors.append(
            _factor(
                kind=kind,
                summary=(
                    f"Project evidence supports {technology.level} technology "
                    f"'{technology.name}'"
                    + (" (generic stack term)." if generic else ".")
                ),
                job_evidence=[
                    {
                        "source": "technology",
                        "item_index": index,
                        "name": technology.name,
                        "excerpt": _job_tech_excerpt(technology),
                    }
                ],
                profile_evidence=[
                    {
                        "source": "project",
                        "ref": f"project:{project.id}",
                        "excerpt": matched_excerpt,
                    }
                ],
            )
        )

    for family, job_hit in job_capabilities.items():
        project_phrase = _first_capability_phrase(
            project_capability_text, _CAPABILITY_FAMILIES[family]
        )
        if project_phrase is None:
            continue
        score.capability_overlap += 1
        score.factors.append(
            _factor(
                kind="capability_overlap",
                summary=(
                    f"Project demonstrates '{family.replace('_', ' ')}' capability "
                    f"overlapping job evidence '{_clip(job_hit['excerpt'])}'."
                ),
                job_evidence=[job_hit["job_evidence"]],
                profile_evidence=[
                    {
                        "source": "project",
                        "ref": f"project:{project.id}",
                        "excerpt": _clip(project_phrase),
                    }
                ],
            )
        )

    for index, responsibility in enumerate(job_analysis.responsibilities):
        responsibility_tokens = _significant_tokens(responsibility.description)
        if not responsibility_tokens:
            continue

        demo_overlap = responsibility_tokens & demonstrates_tokens
        if demo_overlap:
            score.demonstrates_overlap += 1
            score.factors.append(
                _factor(
                    kind="demonstrates_overlap",
                    summary=(
                        "Project demonstrates capabilities overlapping responsibility "
                        f"'{_clip(responsibility.description)}'."
                    ),
                    job_evidence=[
                        {
                            "source": "responsibility",
                            "item_index": index,
                            "excerpt": _job_responsibility_excerpt(responsibility),
                        }
                    ],
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": f"project:{project.id}",
                            "excerpt": _clip(
                                _first_demonstrates_excerpt(project, demo_overlap)
                            ),
                        }
                    ],
                )
            )

        field_overlap = responsibility_tokens & responsibility_field_tokens
        if field_overlap:
            score.responsibility_overlap += 1
            score.factors.append(
                _factor(
                    kind="responsibility_overlap",
                    summary=(
                        "Project summary, outcomes, or technologies overlap "
                        f"responsibility '{_clip(responsibility.description)}'."
                    ),
                    job_evidence=[
                        {
                            "source": "responsibility",
                            "item_index": index,
                            "excerpt": _job_responsibility_excerpt(responsibility),
                        }
                    ],
                    profile_evidence=[
                        {
                            "source": "project",
                            "ref": f"project:{project.id}",
                            "excerpt": _clip(
                                _first_field_excerpt(project, field_overlap)
                            ),
                        }
                    ],
                )
            )

    return score


def _job_capability_families(job_analysis: JobAnalysis) -> dict[str, dict[str, Any]]:
    """Map capability family → first job evidence hit supporting that family."""
    found: dict[str, dict[str, Any]] = {}

    for index, technology in enumerate(job_analysis.technologies):
        text = technology.name
        for family, phrases in _CAPABILITY_FAMILIES.items():
            if family in found:
                continue
            phrase = _first_capability_phrase(text, phrases)
            if phrase is None:
                continue
            found[family] = {
                "excerpt": technology.name,
                "job_evidence": {
                    "source": "technology",
                    "item_index": index,
                    "name": technology.name,
                    "excerpt": _job_tech_excerpt(technology),
                },
            }

    for index, responsibility in enumerate(job_analysis.responsibilities):
        text = responsibility.description
        for family, phrases in _CAPABILITY_FAMILIES.items():
            if family in found:
                continue
            phrase = _first_capability_phrase(text, phrases)
            if phrase is None:
                continue
            found[family] = {
                "excerpt": responsibility.description,
                "job_evidence": {
                    "source": "responsibility",
                    "item_index": index,
                    "excerpt": _job_responsibility_excerpt(responsibility),
                },
            }

    for index, requirement in enumerate(job_analysis.experience_requirements):
        text = requirement.description
        for family, phrases in _CAPABILITY_FAMILIES.items():
            if family in found:
                continue
            phrase = _first_capability_phrase(text, phrases)
            if phrase is None:
                continue
            found[family] = {
                "excerpt": requirement.description,
                "job_evidence": {
                    "source": "experience_requirement",
                    "item_index": index,
                    "excerpt": _clip(
                        requirement.evidence[0].excerpt
                        if requirement.evidence
                        else requirement.description
                    ),
                },
            }

    return found


def _first_capability_phrase(text: str, phrases: tuple[str, ...]) -> str | None:
    # Longer phrases first so "generative ai" wins over "generative".
    for phrase in sorted(phrases, key=len, reverse=True):
        if _phrase_in_text(phrase, text):
            return phrase
    return None


def _technology_factor_kind(level: str) -> str:
    if level == "required":
        return "required_technology"
    if level == "preferred":
        return "preferred_technology"
    return "unspecified_technology"


def _technology_match_excerpt(
    technology_name: str,
    project: Project,
    searchable: str,
) -> str | None:
    needle = technology_name.casefold().strip()
    if not needle:
        return None

    for tech in project.technologies:
        if tech.casefold().strip() == needle:
            return tech

    if _phrase_in_text(needle, searchable):
        for candidate in (
            *project.technologies,
            *project.demonstrates,
            project.summary,
            *project.outcomes,
        ):
            if _phrase_in_text(needle, candidate):
                return _clip(candidate)
        return _clip(technology_name)

    return None


def _phrase_in_text(phrase: str, text: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(phrase.casefold())}(?![a-z0-9])"
    return re.search(pattern, text.casefold()) is not None


def _project_searchable_text(project: Project) -> str:
    parts = [
        *project.technologies,
        *project.demonstrates,
        project.summary,
        *project.outcomes,
    ]
    return " ".join(parts)


def _significant_tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(text.casefold())
        if token not in _STOPWORDS and len(token) >= 2
    }


def _first_demonstrates_excerpt(project: Project, overlap: set[str]) -> str:
    for item in project.demonstrates:
        if _significant_tokens(item) & overlap:
            return item
    return project.demonstrates[0] if project.demonstrates else project.summary


def _first_field_excerpt(project: Project, overlap: set[str]) -> str:
    for item in (project.summary, *project.outcomes, *project.technologies):
        if _significant_tokens(item) & overlap:
            return item
    return project.summary


def _job_tech_excerpt(technology: TechnologyRequirement) -> str:
    if technology.evidence:
        return _clip(technology.evidence[0].excerpt)
    return _clip(technology.name)


def _job_responsibility_excerpt(responsibility: Responsibility) -> str:
    if responsibility.evidence:
        return _clip(responsibility.evidence[0].excerpt)
    return _clip(responsibility.description)


def _clip(text: str, limit: int = 160) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _factor(
    *,
    kind: str,
    summary: str,
    job_evidence: list[dict[str, Any]],
    profile_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": kind,
        "summary": summary,
        "job_evidence": job_evidence,
        "profile_evidence": profile_evidence,
    }


def _build_ranked_projects(scores: list[_ProjectScore]) -> list[dict[str, Any]]:
    tie_groups = _assign_tie_groups(scores)
    ranked: list[dict[str, Any]] = []
    for index, score in enumerate(scores):
        entry: dict[str, Any] = {
            "rank": index + 1,
            "project_id": score.project.id,
            "rationale": _project_rationale(score),
            "factors": score.factors,
        }
        tie_group = tie_groups.get(score.project.id)
        if tie_group is not None:
            entry["tie_group"] = tie_group
            entry["tie_break_reason"] = _TIE_BREAK_REASON
        ranked.append(entry)
    return ranked


def _assign_tie_groups(scores: list[_ProjectScore]) -> dict[str, int]:
    groups: dict[str, int] = {}
    tie_group = 1
    index = 0
    while index < len(scores):
        end = index + 1
        while (
            end < len(scores)
            and scores[end].primary_key == scores[index].primary_key
        ):
            end += 1
        if end - index > 1:
            for score in scores[index:end]:
                groups[score.project.id] = tie_group
            tie_group += 1
        index = end
    return groups


def _project_rationale(score: _ProjectScore) -> str:
    parts: list[str] = []
    if score.distinctive_required_technology:
        parts.append(
            f"{score.distinctive_required_technology} distinctive required "
            "technology hit(s)"
        )
    if score.distinctive_preferred_technology:
        parts.append(
            f"{score.distinctive_preferred_technology} distinctive preferred "
            "technology hit(s)"
        )
    if score.demonstrates_overlap:
        parts.append(f"{score.demonstrates_overlap} demonstrates overlap(s)")
    if score.responsibility_overlap:
        parts.append(f"{score.responsibility_overlap} responsibility overlap(s)")
    if score.capability_overlap:
        parts.append(f"{score.capability_overlap} capability overlap(s)")
    if score.generic_required_technology:
        parts.append(
            f"{score.generic_required_technology} generic required technology hit(s)"
        )
    if score.generic_preferred_technology:
        parts.append(
            f"{score.generic_preferred_technology} generic preferred technology hit(s)"
        )
    if score.unspecified_technology:
        parts.append(f"{score.unspecified_technology} unspecified technology hit(s)")
    if not parts:
        return f"Project '{score.project.id}' ranked with supporting evidence."
    return (
        f"Project '{score.project.id}' ranked on "
        + ", ".join(parts)
        + "."
    )


def _build_summary(
    ranked_projects: list[dict[str, Any]],
    unranked_ids: list[str],
) -> str:
    if not ranked_projects:
        return (
            "No portfolio projects had overlapping technologies or responsibilities "
            f"with the job analysis; {len(unranked_ids)} project(s) remain unranked."
        )
    lead = ranked_projects[0]["project_id"]
    ranked_count = len(ranked_projects)
    unranked_count = len(unranked_ids)
    return (
        f"Ranked {ranked_count} project(s); lead with '{lead}'. "
        f"{unranked_count} project(s) had no matching factors."
    )
