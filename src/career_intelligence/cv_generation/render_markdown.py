"""Deterministic Markdown rendering of an approved TailoringPlan.

Presentation lives here (FR-006b): submit-ready layout, hierarchy, scanning
aids, and strategic bolding. Content selection remains plan-owned.
"""

from __future__ import annotations

import re
from typing import Literal

from career_intelligence.cv_generation.models import (
    RenderedExperience,
    RenderedProject,
    RenderedSkill,
    TailoredCv,
)
from career_intelligence.cv_generation.options import ContactDetails

PresentationMode = Literal["submit", "review"]

# Cap residual skills on the submit surface; full inventory remains in JSON.
_MAX_ADDITIONAL_SKILLS_SUBMIT = 8

_KIND_LABELS = {
    "employment": None,
    "independent_engineering": "Independent engineering",
    "professional_development": "Professional development",
}

_CONTACT_ORDER = (
    "email",
    "phone",
    "location",
    "linkedin_url",
    "portfolio_url",
    "github_url",
)


def render_markdown(
    cv: TailoredCv,
    *,
    presentation: PresentationMode = "submit",
) -> str:
    """Render Markdown CV from structured TailoredCv fields.

    ``presentation="submit"`` (default) produces an employer-facing document.
    ``presentation="review"`` retains internal plan/meta cues for owner debug.
    """
    if presentation == "review":
        return _render_review(cv)
    return _render_submit(cv)


def contact_as_dict(contact: ContactDetails | None) -> dict[str, str] | None:
    if contact is None:
        return None
    payload = contact.model_dump(exclude_none=True)
    return {key: value for key, value in payload.items() if value} or None


def _render_submit(cv: TailoredCv) -> str:
    emphasis = _emphasis_terms(cv)
    lines: list[str] = []

    lines.append(f"# {cv.full_name}")
    lines.append("")
    contact_lines = _format_contact_lines(cv.contact)
    for contact_line in contact_lines:
        lines.append(contact_line)
    if contact_lines:
        lines.append("")
    lines.append(f"**{cv.target_role}**")
    lines.append("")
    lines.append("---")
    lines.append("")

    if cv.summary:
        lines.append("## Professional Summary")
        lines.append("")
        # Do not bold inside the summary paragraph — phrase-level bolding can
        # split portfolio project names that Phase C may mention in prose.
        lines.append(cv.summary)
        lines.append("")

    if cv.selected_engineering_highlights:
        lines.append("## Selected Engineering Highlights")
        lines.append("")
        for highlight in cv.selected_engineering_highlights:
            lines.append(f"- {_bold_terms(highlight, emphasis)}")
        lines.append("")

    emphasised, additional = _curate_skills_for_submit(cv.skills)
    if emphasised or additional:
        lines.append("## Core Skills")
        lines.append("")
        if emphasised:
            lines.append(
                " · ".join(f"**{skill.skill_name}**" for skill in emphasised)
            )
            lines.append("")
        if additional:
            lines.append(
                "**Also:** "
                + " · ".join(skill.skill_name for skill in additional)
            )
            lines.append("")

    if cv.experience:
        lines.append("## Professional Experience")
        lines.append("")
        for entry in cv.experience:
            lines.extend(_render_experience_block(entry, emphasis))

    if cv.projects:
        lines.append("## Featured AI Projects")
        lines.append("")
        for project in cv.projects:
            lines.extend(_render_project_block(project, emphasis))

    if cv.engineering_methodology is not None:
        lines.append("## AI Engineering Methodology")
        lines.append("")
        lines.append(cv.engineering_methodology.philosophy)
        lines.append("")
        for category in cv.engineering_methodology.categories:
            practices = " · ".join(category.practices)
            lines.append(f"**{category.name}:** {practices}")
            lines.append("")

    if cv.certifications:
        lines.append("## Certifications")
        lines.append("")
        for cert in cv.certifications:
            lines.append(f"- **{cert.name}** — {cert.issuer}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_review(cv: TailoredCv) -> str:
    """Owner-debug surface: plan themes, skill categories, guidance footer."""
    lines: list[str] = []
    lines.append(f"# {cv.full_name}")
    lines.append("")
    lines.append(f"**Target role:** {cv.target_role}")
    lines.append("")
    lines.append("> Owner review required before any external use.")
    lines.append("")

    if cv.contact:
        lines.append("## Contact")
        lines.append("")
        for key, value in cv.contact.items():
            lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        lines.append("")

    if cv.summary:
        lines.append("## Summary")
        lines.append("")
        lines.append(cv.summary)
        lines.append("")

    if cv.summary_themes:
        lines.append("## Summary themes (from Tailoring Plan)")
        lines.append("")
        for theme in cv.summary_themes:
            lines.append(f"- {theme}")
        lines.append("")
        lines.append(_summary_source_note(cv))
        lines.append("")

    emphasised = [skill for skill in cv.skills if skill.emphasised]
    other = [skill for skill in cv.skills if not skill.emphasised]
    if emphasised or other:
        lines.append("## Skills")
        lines.append("")
        if emphasised:
            lines.append("### Emphasised")
            lines.append("")
            for skill in emphasised:
                lines.append(f"- {skill.skill_name} ({skill.category})")
            lines.append("")
        if other:
            lines.append("### Additional")
            lines.append("")
            for skill in other:
                lines.append(f"- {skill.skill_name} ({skill.category})")
            lines.append("")

    if cv.projects:
        lines.append("## Projects")
        lines.append("")
        for project in cv.projects:
            lines.extend(_render_project_block(project, set(), review=True))

    if cv.experience:
        lines.append("## Experience")
        lines.append("")
        for entry in cv.experience:
            end = entry.end_date or "Present"
            lines.append(f"### {entry.title} — {entry.organisation}")
            lines.append("")
            lines.append(f"*{entry.start_date} – {end}* · `{entry.kind}`")
            if entry.location:
                lines.append("")
                lines.append(entry.location)
            lines.append("")
            for highlight in entry.highlights:
                lines.append(f"- {highlight}")
            if entry.technologies:
                lines.append("")
                lines.append(
                    "**Technologies:** " + ", ".join(entry.technologies)
                )
            lines.append("")

    if cv.certifications:
        lines.append("## Certifications (profile baseline — not tailored)")
        lines.append("")
        for cert in cv.certifications:
            lines.append(f"- {cert.name} ({cert.issuer}) — {cert.status}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"_Experience guidance: `{cv.experience_guidance_kind}`. "
        "This draft must not be submitted without owner review._"
    )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _summary_source_note(cv: TailoredCv) -> str:
    if cv.summary_source in {"openai_rewrite", "fixture_rewrite"}:
        return (
            "_Summary prose was rewritten in Phase C against these themes; "
            "themes are retained for owner review._"
        )
    if cv.summary_source == "fallback_profile_copy":
        return (
            "_Summary rewrite fell back to the career-profile summary; "
            "themes are retained for owner review._"
        )
    if cv.summary_source == "theme_aware_composition":
        return (
            "_Summary lead was composed deterministically from Tailoring Plan "
            "themes; body retained from the career profile._"
        )
    return (
        "_Summary prose is copied from the career profile "
        "(rewrite_summary disabled or skipped); theme-guided rewriting "
        "is available via Phase C when enabled._"
    )


def _curate_skills_for_submit(
    skills: list[RenderedSkill],
) -> tuple[list[RenderedSkill], list[RenderedSkill]]:
    emphasised = [skill for skill in skills if skill.emphasised]
    # Prefer technical/domain residuals that support scanning; drop long soft lists.
    residuals = [
        skill
        for skill in skills
        if not skill.emphasised and skill.category in {"technical", "domain"}
    ]
    additional = residuals[:_MAX_ADDITIONAL_SKILLS_SUBMIT]
    return emphasised, additional


def _format_month(value: str) -> str:
    """Format ``YYYY-MM`` as ``Mon YYYY`` for submit-ready presentation."""
    months = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )
    parts = value.split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        month_index = int(parts[1])
        if 1 <= month_index <= 12:
            return f"{months[month_index - 1]} {parts[0]}"
    return value


def _render_experience_block(
    entry: RenderedExperience,
    emphasis: set[str],
) -> list[str]:
    lines: list[str] = []
    end = _format_month(entry.end_date) if entry.end_date else "Present"
    start = _format_month(entry.start_date)
    lines.append(f"### {entry.title} — {entry.organisation}")
    lines.append("")
    meta_parts = [f"{start} – {end}"]
    kind_label = _KIND_LABELS.get(entry.kind)
    if kind_label:
        meta_parts.append(kind_label)
    if entry.location:
        meta_parts.append(entry.location)
    lines.append(f"*{' · '.join(meta_parts)}*")
    lines.append("")
    for highlight in entry.highlights:
        lines.append(f"- {_bold_terms(highlight, emphasis)}")
    if entry.technologies:
        lines.append("")
        lines.append(
            "**Technologies:** " + _format_tech_list(entry.technologies, emphasis)
        )
    lines.append("")
    return lines


def _render_project_block(
    project: RenderedProject,
    emphasis: set[str],
    *,
    review: bool = False,
) -> list[str]:
    lines: list[str] = []
    lines.append(f"### {project.name}")
    lines.append("")
    # Keep project summaries unbolded so full project titles remain intact for
    # scanners and fidelity checks when titles appear in nearby prose.
    if review:
        lines.append(project.summary)
    else:
        lines.append(f"**Overview:** {project.summary}")
    lines.append("")
    if project.demonstrates:
        label = "**Demonstrates:**" if review else "**Engineering Highlights:**"
        lines.append(label)
        lines.append("")
        for item in project.demonstrates:
            text = item if review else _bold_terms(item, emphasis)
            lines.append(f"- {text}")
        lines.append("")
    if project.outcomes and not review:
        lines.append("**Outcomes:**")
        lines.append("")
        for outcome in project.outcomes:
            lines.append(f"- {_bold_terms(outcome, emphasis)}")
        lines.append("")
    elif project.outcomes and review:
        lines.append("**Outcomes:**")
        lines.append("")
        for outcome in project.outcomes:
            lines.append(f"- {outcome}")
        lines.append("")
    if project.technologies:
        techs = (
            ", ".join(project.technologies)
            if review
            else " · ".join(
                f"**{tech}**" if tech.casefold() in {t.casefold() for t in emphasis} else tech
                for tech in project.technologies
            )
        )
        label = "**Technologies:**" if review else "**Technology Stack:**"
        lines.append(f"{label} {techs}")
        lines.append("")
    return lines


def _format_contact_lines(contact: dict[str, str] | None) -> list[str]:
    """Return one or more contact lines for submit-ready Markdown."""
    if not contact:
        return []
    primary: list[str] = []
    links: list[str] = []
    for key in _CONTACT_ORDER:
        value = contact.get(key)
        if not value:
            continue
        if key == "email":
            primary.append(f"[{value}](mailto:{value})")
        elif key == "phone":
            tel = "".join(ch for ch in value if ch.isdigit() or ch == "+")
            if tel.startswith("0") and len(tel) == 10:
                tel = f"+61{tel[1:]}"
            primary.append(f"[{value}](tel:{tel})")
        elif key == "location":
            primary.insert(0, value)
        elif key == "linkedin_url":
            links.append(f"LinkedIn: [{value}]({value})")
        elif key == "portfolio_url":
            links.append(f"Portfolio: [{value}]({value})")
        elif key == "github_url":
            links.append(f"GitHub: [{value}]({value})")
    for key, value in contact.items():
        if key not in _CONTACT_ORDER and value:
            primary.append(value)
    lines: list[str] = []
    if primary:
        lines.append(" · ".join(primary))
    lines.extend(links)
    return lines


def _format_contact_line(contact: dict[str, str] | None) -> str | None:
    lines = _format_contact_lines(contact)
    return " · ".join(lines) if lines else None


def _emphasis_terms(cv: TailoredCv) -> set[str]:
    """Terms used for strategic bolding in bullets and technology lists.

    Limited to promoted skills and summary themes so scanning highlights the
    plan's priorities without over-bolding every portfolio technology.
    """
    terms: set[str] = set()
    for skill in cv.skills:
        if skill.emphasised:
            terms.add(skill.skill_name)
    for theme in cv.summary_themes:
        terms.add(theme)
    return {term for term in terms if len(term.strip()) >= 2}


def _format_tech_list(technologies: list[str], emphasis: set[str]) -> str:
    rendered: list[str] = []
    emphasis_folded = {term.casefold() for term in emphasis}
    for tech in technologies:
        if tech.casefold() in emphasis_folded:
            rendered.append(f"**{tech}**")
        else:
            rendered.append(tech)
    return ", ".join(rendered)


def _bold_terms(text: str, terms: set[str]) -> str:
    """Bold whole-word / phrase matches for emphasis terms (longest first)."""
    if not text or not terms:
        return text
    # Skip terms already inside markdown emphasis markers by working on plain text.
    ordered = sorted(terms, key=len, reverse=True)
    result = text
    for term in ordered:
        pattern = re.compile(rf"(?<!\*)\b({re.escape(term)})\b(?!\*)", re.IGNORECASE)
        result = pattern.sub(r"**\1**", result)
    return result
