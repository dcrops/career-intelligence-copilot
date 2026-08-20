"""Adapt Master CV Markdown using an approved TailoringPlan.

Keeps Master editorial prose (summary, experience, project overviews).
Applies plan-owned inclusion/order for featured projects and rebuilds the
skills scan line. Does not invent claims.
"""

from __future__ import annotations

import re
from pathlib import Path

from career_intelligence.cv_generation.models import RenderedSkill, TailoringPlan
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.cv_generation.render_markdown import (
    _curate_skills_for_submit,
    _format_contact_lines,
    contact_as_dict,
)
from career_intelligence.profile.models import CareerProfile

_HEADING2 = re.compile(r"^##\s+(.+)$")
_HEADING3 = re.compile(r"^###\s+(.+)$")

DEFAULT_MASTER_CV_PATH = (
    Path(__file__).resolve().parents[3]
    / "career-documents"
    / "cv"
    / "master_ai_engineer_cv.md"
)

_SKILLS_HEADINGS = frozenset({"technical skills", "core skills"})
_PROJECTS_HEADING = "featured ai projects"
_METHODOLOGY_HEADING = "ai engineering methodology"


def load_master_cv_markdown(path: Path | None = None) -> str:
    resolved = path or DEFAULT_MASTER_CV_PATH
    return resolved.read_text(encoding="utf-8")


def adapt_master_cv_markdown(
    master_markdown: str,
    *,
    profile: CareerProfile,
    plan: TailoringPlan,
    target_role: str,
    contact: ContactDetails | None,
    omit_methodology: bool = True,
    summary_override: str | None = None,
    highlight_override: list[str] | None = None,
    project_relevance_lines: dict[str, str] | None = None,
) -> str:
    """Return tailored Markdown derived from the Master CV.

    Optional overrides are the M3 rewrite surface. Production ``cic package
    prepare`` does not pass them. Locked H2 sections stay Master prose unless
    an override is supplied.
    """
    sections = _split_h2_sections(master_markdown)
    header = _adapt_header(sections["__header__"], target_role, contact)
    projects_by_id = {project.id: project for project in profile.projects}
    ordered_names: list[str] = []
    for item in plan.projects_to_emphasise:
        project = projects_by_id.get(item.project_id)
        if project is not None:
            ordered_names.append(project.name)

    skills_block = _render_skills_section(plan)
    relevance = {
        key.casefold(): value.strip()
        for key, value in (project_relevance_lines or {}).items()
        if value.strip()
    }
    body_parts: list[str] = []
    for heading, body in sections["__order__"]:
        key = heading.casefold()
        if key in _SKILLS_HEADINGS:
            body_parts.append(skills_block)
            continue
        if key == _PROJECTS_HEADING:
            body_parts.append(
                _render_projects_section(
                    body,
                    ordered_names,
                    relevance_lines=relevance,
                )
            )
            continue
        if omit_methodology and key == _METHODOLOGY_HEADING:
            continue
        if key == "professional summary" and summary_override is not None:
            body_parts.append(f"## {heading}\n\n{summary_override.strip()}\n")
            continue
        if key == "selected engineering highlights" and highlight_override is not None:
            bullets = "\n".join(f"- {item}" for item in highlight_override)
            body_parts.append(f"## {heading}\n\n{bullets}\n")
            continue
        body_parts.append(f"## {heading}\n\n{body.strip()}\n")

    text = header.rstrip() + "\n\n" + "\n".join(part.rstrip() + "\n" for part in body_parts)
    text = re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"
    text = re.sub(
        r"\n\*Canonical Master CV v4\.[^*]*\*\s*$",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    return text.rstrip() + "\n"


def extract_master_summary(master_markdown: str) -> str | None:
    sections = _split_h2_sections(master_markdown)
    for heading, body in sections["__order__"]:
        if heading.casefold() == "professional summary":
            return body.strip() or None
    return None


def extract_master_highlights(master_markdown: str) -> list[str]:
    sections = _split_h2_sections(master_markdown)
    for heading, body in sections["__order__"]:
        if heading.casefold() == "selected engineering highlights":
            return _extract_bullets(body)
    return []


def extract_master_project_bodies(master_markdown: str) -> dict[str, str]:
    sections = _split_h2_sections(master_markdown)
    for heading, body in sections["__order__"]:
        if heading.casefold() == _PROJECTS_HEADING:
            return {name: text.strip() for name, text in _split_h3_blocks(body)}
    return {}


def extract_h2_section(master_markdown: str, heading: str) -> str | None:
    target = heading.casefold()
    sections = _split_h2_sections(master_markdown)
    for name, body in sections["__order__"]:
        if name.casefold() == target:
            return body.strip()
    return None


def _split_h2_sections(markdown: str) -> dict[str, object]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    header_lines: list[str] = []
    order: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_body: list[str] = []
    for line in lines:
        match = _HEADING2.match(line)
        if match:
            if current_heading is None:
                header_lines = list(header_lines)
            else:
                order.append((current_heading, "\n".join(current_body)))
            current_heading = match.group(1).strip()
            current_body = []
            continue
        if current_heading is None:
            header_lines.append(line)
        else:
            current_body.append(line)
    if current_heading is not None:
        order.append((current_heading, "\n".join(current_body)))
    return {"__header__": "\n".join(header_lines), "__order__": order}


def _adapt_header(
    header: str,
    target_role: str,
    contact: ContactDetails | None,
) -> str:
    lines = header.split("\n")
    name_line = lines[0] if lines and lines[0].startswith("# ") else "# Candidate"
    contact_payload = contact_as_dict(contact)
    contact_lines = _format_contact_lines(contact_payload)
    parts = [name_line, ""]
    parts.extend(contact_lines)
    if contact_lines:
        parts.append("")
    parts.append(f"**{target_role}**")
    parts.append("")
    parts.append("---")
    return "\n".join(parts)


def _render_skills_section(plan: TailoringPlan) -> str:
    rendered: list[RenderedSkill] = []
    for item in plan.skills_to_promote:
        rendered.append(
            RenderedSkill(
                skill_name=item.skill_name,
                category=item.category,
                emphasised=True,
            )
        )
    for item in plan.skills_not_emphasised:
        rendered.append(
            RenderedSkill(
                skill_name=item.skill_name,
                category=item.category,
                emphasised=False,
            )
        )
    emphasised, additional = _curate_skills_for_submit(rendered)
    lines = ["## Core Skills", ""]
    if emphasised:
        lines.append(" · ".join(f"**{skill.skill_name}**" for skill in emphasised))
        lines.append("")
    if additional:
        lines.append(
            "**Also:** " + " · ".join(skill.skill_name for skill in additional)
        )
        lines.append("")
    return "\n".join(lines)


def _render_projects_section(
    master_projects_body: str,
    ordered_names: list[str],
    *,
    relevance_lines: dict[str, str] | None = None,
) -> str:
    blocks = _split_h3_blocks(master_projects_body)
    by_name = {name.casefold(): (name, body) for name, body in blocks}
    lines = ["## Featured AI Projects", ""]
    for name in ordered_names:
        match = by_name.get(name.casefold())
        if match is None:
            continue
        heading, body = match
        lines.append(f"### {heading}")
        lines.append("")
        relevance = (relevance_lines or {}).get(heading.casefold())
        if relevance:
            lines.append(f"*Relevant to this role: {relevance}*")
            lines.append("")
        lines.append(body.strip())
        lines.append("")
    return "\n".join(lines)


def _extract_bullets(body: str) -> list[str]:
    bullets: list[str] = []
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _split_h3_blocks(body: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    current: str | None = None
    current_body: list[str] = []
    for line in body.split("\n"):
        match = _HEADING3.match(line)
        if match:
            if current is not None:
                blocks.append((current, "\n".join(current_body)))
            current = match.group(1).strip()
            current_body = []
            continue
        if current is not None:
            current_body.append(line)
    if current is not None:
        blocks.append((current, "\n".join(current_body)))
    return blocks
