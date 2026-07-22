"""Deterministic portfolio matcher for FR-004.

Package-private production ranking path. Returns an untrusted payload; callers
must obtain trusted output through PortfolioMatchingService.
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

_TIE_BREAK_REASON = (
    "Equal primary ranking signals; ordered by stable project_id ascending"
)


@dataclass(frozen=True)
class _PrimaryKey:
    required_technology: int
    preferred_technology: int
    demonstrates_overlap: int
    responsibility_overlap: int
    unspecified_technology: int


@dataclass
class _ProjectScore:
    project: Project
    required_technology: int = 0
    preferred_technology: int = 0
    demonstrates_overlap: int = 0
    responsibility_overlap: int = 0
    unspecified_technology: int = 0
    factors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def primary_key(self) -> _PrimaryKey:
        return _PrimaryKey(
            required_technology=self.required_technology,
            preferred_technology=self.preferred_technology,
            demonstrates_overlap=self.demonstrates_overlap,
            responsibility_overlap=self.responsibility_overlap,
            unspecified_technology=self.unspecified_technology,
        )

    @property
    def has_factors(self) -> bool:
        return bool(self.factors)

    def sort_key(self) -> tuple[int, int, int, int, int, str]:
        return (
            -self.required_technology,
            -self.preferred_technology,
            -self.demonstrates_overlap,
            -self.responsibility_overlap,
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

        scores = [_score_project(project, job_analysis) for project in profile.projects]
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


def _score_project(project: Project, job_analysis: JobAnalysis) -> _ProjectScore:
    score = _ProjectScore(project=project)
    searchable = _project_searchable_text(project)
    demonstrates_tokens = _significant_tokens(
        " ".join(project.demonstrates)
    )
    responsibility_field_tokens = _significant_tokens(
        " ".join(
            [
                project.summary,
                *project.outcomes,
                *project.technologies,
            ]
        )
    )

    for index, technology in enumerate(job_analysis.technologies):
        matched_excerpt = _technology_match_excerpt(technology.name, project, searchable)
        if matched_excerpt is None:
            continue
        kind = _technology_factor_kind(technology.level)
        if kind == "required_technology":
            score.required_technology += 1
        elif kind == "preferred_technology":
            score.preferred_technology += 1
        else:
            score.unspecified_technology += 1
        score.factors.append(
            _factor(
                kind=kind,
                summary=(
                    f"Project evidence supports {technology.level} technology "
                    f"'{technology.name}'."
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
    pattern = (
        rf"(?<![a-z0-9]){re.escape(phrase.casefold())}(?![a-z0-9])"
    )
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
    if score.required_technology:
        parts.append(f"{score.required_technology} required technology hit(s)")
    if score.preferred_technology:
        parts.append(f"{score.preferred_technology} preferred technology hit(s)")
    if score.demonstrates_overlap:
        parts.append(f"{score.demonstrates_overlap} demonstrates overlap(s)")
    if score.responsibility_overlap:
        parts.append(f"{score.responsibility_overlap} responsibility overlap(s)")
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
