"""Summary rewrite contracts for FR-006 Phase C.

The rewriter is a rendering layer only. It consumes plan-derived structured
input and returns untrusted summary prose for validation by the service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

SUMMARY_PROMPT_VERSION = "v2"
SUMMARY_TARGET_MIN_WORDS = 70
SUMMARY_TARGET_MAX_WORDS = 110
SUMMARY_HARD_MAX_WORDS = 140

SummarySource = Literal[
    "profile_copy",
    "openai_rewrite",
    "fixture_rewrite",
    "fallback_profile_copy",
]


class SummaryRewriteExtraction(BaseModel):
    """Untrusted structured LLM/fixture output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: NonEmptyString


@dataclass(frozen=True)
class SummaryThemeInput:
    rank: int
    theme: str
    rationale: str


@dataclass(frozen=True)
class PreferredSkillInput:
    skill_name: str
    category: str


@dataclass(frozen=True)
class PreferredProjectInput:
    name: str
    summary: str
    outcomes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SummaryRewriteInput:
    """Plan-derived inputs only — never includes raw job description text."""

    source_summary: str
    mandatory_themes: tuple[SummaryThemeInput, ...]
    preferred_skills: tuple[PreferredSkillInput, ...]
    preferred_projects: tuple[PreferredProjectInput, ...]
    allowed_technologies: tuple[str, ...]
    prohibited_technologies: tuple[str, ...]
    allowed_employers: tuple[str, ...]
    allowed_project_names: tuple[str, ...]
    allowed_certifications: tuple[str, ...]
    constraints: tuple[str, ...] = field(default_factory=tuple)
    prompt_version: str = SUMMARY_PROMPT_VERSION


class SummaryRewriter(Protocol):
    """Package-private rewriter seam (OpenAI or fixture)."""

    def rewrite(self, rewrite_input: SummaryRewriteInput) -> SummaryRewriteExtraction:
        """Return untrusted structured summary prose."""
        ...
