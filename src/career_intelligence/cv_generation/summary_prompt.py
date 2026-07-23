"""Load and format Phase C summary-rewrite prompts from versioned files."""

from __future__ import annotations

import json
from pathlib import Path

from .summary_rewriter import SUMMARY_PROMPT_VERSION, SummaryRewriteInput

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

__all__ = [
    "SUMMARY_PROMPT_VERSION",
    "format_summary_rewrite_input",
    "load_summary_instructions",
    "prompt_path",
]


def prompt_path(version: str = SUMMARY_PROMPT_VERSION) -> Path:
    return _PROMPTS_DIR / f"cv_summary_{version}.md"


def load_summary_instructions(version: str = SUMMARY_PROMPT_VERSION) -> str:
    """Load production instructions from disk (not embedded in Python)."""
    path = prompt_path(version)
    if not path.is_file():
        raise FileNotFoundError(f"Summary prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def format_summary_rewrite_input(rewrite_input: SummaryRewriteInput) -> str:
    """Render structured tagged blocks for the model (no raw JD)."""
    themes = [
        {
            "rank": item.rank,
            "theme": item.theme,
            "rationale": item.rationale,
        }
        for item in rewrite_input.mandatory_themes
    ]
    skills = [
        {"skill_name": item.skill_name, "category": item.category}
        for item in rewrite_input.preferred_skills
    ]
    projects = [
        {
            "name": item.name,
            "summary": item.summary,
            "outcomes": list(item.outcomes),
        }
        for item in rewrite_input.preferred_projects
    ]
    parts = [
        _tagged("SourceSummary", rewrite_input.source_summary),
        _tagged("MandatoryThemes", _json(themes)),
        _tagged("PreferredSkills", _json(skills)),
        _tagged("PreferredProjects", _json(projects)),
        _tagged(
            "AllowedTechnologyVocabulary",
            _json(list(rewrite_input.allowed_technologies)),
        ),
        _tagged(
            "ProhibitedTechnologies",
            _json(list(rewrite_input.prohibited_technologies)),
        ),
        _tagged("AllowedEmployers", _json(list(rewrite_input.allowed_employers))),
        _tagged(
            "AllowedProjectNames",
            _json(list(rewrite_input.allowed_project_names)),
        ),
        _tagged(
            "AllowedCertifications",
            _json(list(rewrite_input.allowed_certifications)),
        ),
        _tagged("Constraints", _json(list(rewrite_input.constraints))),
        _tagged("PromptVersion", rewrite_input.prompt_version),
    ]
    return "\n\n".join(parts)


def _tagged(name: str, body: str) -> str:
    return f"<{name}>\n{body}\n</{name}>"


def _json(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
