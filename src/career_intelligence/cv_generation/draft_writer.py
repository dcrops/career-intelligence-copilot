"""Deterministic draft writers for approved TailoredCv artifacts.

Writes Markdown and typed JSON under a caller-supplied directory (default
operational location: ``career-documents/cv/generated/``).

No PDF/DOCX. No submission or email. Owner review remains mandatory.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from career_intelligence.cv_generation.models import TailoredCv, TailoringPlan

_UNSAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True)
class DraftWriteResult:
    """Paths written for one TailoredCv draft pair."""

    output_dir: Path
    stem: str
    markdown_path: Path
    json_path: Path
    plan_json_path: Path


def default_generated_dir(repo_root: Path) -> Path:
    return repo_root / "career-documents" / "cv" / "generated"


def build_draft_stem(
    *,
    company: str | None,
    title: str | None,
    when: datetime | None = None,
) -> str:
    """Build a repository-consistent filename stem for generated CV drafts."""
    stamp = (when or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    company_part = _slug(company or "company")
    title_part = _slug(title or "role")
    return f"{stamp}_{company_part}_{title_part}"


def write_tailored_cv_drafts(
    cv: TailoredCv,
    plan: TailoringPlan,
    *,
    output_dir: Path,
    stem: str | None = None,
) -> DraftWriteResult:
    """Write Markdown + TailoredCv JSON + TailoringPlan JSON for owner review."""
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_stem = stem or build_draft_stem(
        company=cv.job_analysis.posting.company,
        title=cv.job_analysis.posting.title,
    )
    markdown_path = output_dir / f"{resolved_stem}.md"
    json_path = output_dir / f"{resolved_stem}.json"
    plan_json_path = output_dir / f"{resolved_stem}.tailoring_plan.json"

    markdown_path.write_text(cv.rendered_markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(cv.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    plan_json_path.write_text(
        json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return DraftWriteResult(
        output_dir=output_dir,
        stem=resolved_stem,
        markdown_path=markdown_path,
        json_path=json_path,
        plan_json_path=plan_json_path,
    )


def _slug(value: str) -> str:
    cleaned = _UNSAFE_FILENAME.sub("_", value.strip().casefold())
    cleaned = cleaned.strip("._-")
    return cleaned[:48] or "item"
