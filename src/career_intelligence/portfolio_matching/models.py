"""Typed domain models for FR-004 Portfolio Matching.

These models rank portfolio projects for a trusted JobAnalysis against a trusted
CareerProfile. They intentionally omit fit judgments, application tiers, effort
guidance, apply/skip recommendations, and percentage match scores.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import Identifier

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

RankingFactorKind = Literal[
    "required_technology",
    "preferred_technology",
    "unspecified_technology",
    "responsibility_overlap",
    "demonstrates_overlap",
]

JobEvidenceSource = Literal[
    "role_family",
    "seniority",
    "technology",
    "responsibility",
    "experience_requirement",
    "compensation",
    "location",
    "work_arrangement",
    "employment",
]

ProfileEvidenceSource = Literal["project"]

_LIST_JOB_SOURCES = frozenset(
    {
        "technology",
        "responsibility",
        "experience_requirement",
    }
)


class MatchingModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobEvidenceRef(MatchingModel):
    """Pointer to an analysed job requirement with optional supporting excerpt."""

    source: JobEvidenceSource
    item_index: int | None = Field(default=None, ge=0)
    name: NonEmptyString | None = None
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def list_sources_require_item_index(self) -> JobEvidenceRef:
        if self.source in _LIST_JOB_SOURCES and self.item_index is None:
            raise ValueError(f"{self.source} job evidence requires item_index")
        return self


class ProfileEvidenceRef(MatchingModel):
    """Pointer to a portfolio project. ``ref`` must resolve at service validation."""

    source: ProfileEvidenceSource
    ref: NonEmptyString
    excerpt: NonEmptyString | None = None


class RankingFactor(MatchingModel):
    """One explainable claim supporting a project's rank."""

    kind: RankingFactorKind
    summary: NonEmptyString
    job_evidence: list[JobEvidenceRef] = Field(min_length=1)
    profile_evidence: list[ProfileEvidenceRef] = Field(min_length=1)


class RankedPortfolioProject(MatchingModel):
    """One portfolio project in ranked order for the opportunity."""

    rank: int = Field(ge=1)
    project_id: Identifier
    rationale: NonEmptyString
    factors: list[RankingFactor] = Field(min_length=1)
    tie_group: int | None = Field(default=None, ge=1)
    tie_break_reason: NonEmptyString | None = None

    @model_validator(mode="after")
    def tie_fields_are_consistent(self) -> RankedPortfolioProject:
        if self.tie_group is None:
            if self.tie_break_reason is not None:
                raise ValueError("tie_break_reason is only allowed when tie_group is set")
        elif self.tie_break_reason is None:
            raise ValueError("tie_group requires tie_break_reason")
        return self


class PortfolioMatch(MatchingModel):
    """Trusted ranked portfolio projects for one job analysis.

    ``job_analysis`` is bound by ``PortfolioMatchingService`` from the
    caller-supplied trusted input. The profile is not embedded; project grounding
    lives in ``project:<id>`` profile evidence refs and ``project_id`` fields.
    """

    job_analysis: JobAnalysis
    ranked_projects: list[RankedPortfolioProject] = Field(default_factory=list)
    unranked_project_ids: list[Identifier] = Field(default_factory=list)
    summary: NonEmptyString
    insufficient_evidence: bool = False

    @model_validator(mode="after")
    def ranking_structure_is_consistent(self) -> PortfolioMatch:
        ranked_ids = [entry.project_id for entry in self.ranked_projects]
        if len(ranked_ids) != len(set(ranked_ids)):
            raise ValueError("ranked_projects project_id values must be unique")

        if len(self.unranked_project_ids) != len(set(self.unranked_project_ids)):
            raise ValueError("unranked_project_ids must be unique")

        overlap = set(ranked_ids) & set(self.unranked_project_ids)
        if overlap:
            raise ValueError(
                "project ids cannot appear in both ranked_projects and "
                f"unranked_project_ids: {sorted(overlap)}"
            )

        ranks = [entry.rank for entry in self.ranked_projects]
        if ranks:
            expected = list(range(1, len(ranks) + 1))
            if sorted(ranks) != expected:
                raise ValueError(
                    f"ranked_projects ranks must be contiguous 1..{len(ranks)}, "
                    f"got {sorted(ranks)}"
                )
            if ranks != expected:
                raise ValueError(
                    "ranked_projects must be ordered by ascending rank "
                    f"(expected {expected}, got {ranks})"
                )

        return self
