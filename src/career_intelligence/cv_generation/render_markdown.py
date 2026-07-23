"""Deterministic Markdown rendering of an approved TailoringPlan."""

from __future__ import annotations

from career_intelligence.cv_generation.models import TailoredCv
from career_intelligence.cv_generation.options import ContactDetails


def render_markdown(cv: TailoredCv) -> str:
    """Render a human-reviewable Markdown CV from structured TailoredCv fields.

    This function must not reorder sections relative to the structured fields;
    callers assemble field order from the TailoringPlan before rendering.
    """
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
        if cv.summary_source in {"openai_rewrite", "fixture_rewrite"}:
            note = (
                "_Summary prose was rewritten in Phase C against these themes; "
                "themes are retained for owner review._"
            )
        elif cv.summary_source == "fallback_profile_copy":
            note = (
                "_Summary rewrite fell back to the career-profile summary; "
                "themes are retained for owner review._"
            )
        else:
            note = (
                "_Summary prose is copied from the career profile "
                "(rewrite_summary disabled or skipped); theme-guided rewriting "
                "is available via Phase C when enabled._"
            )
        lines.append(note)
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
            lines.append(f"### {project.name}")
            lines.append("")
            lines.append(project.summary)
            lines.append("")
            if project.technologies:
                lines.append(
                    "**Technologies:** " + ", ".join(project.technologies)
                )
                lines.append("")
            if project.outcomes:
                lines.append("**Outcomes:**")
                lines.append("")
                for outcome in project.outcomes:
                    lines.append(f"- {outcome}")
                lines.append("")
            if project.demonstrates:
                lines.append("**Demonstrates:**")
                lines.append("")
                for item in project.demonstrates:
                    lines.append(f"- {item}")
                lines.append("")

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
                lines.append("**Technologies:** " + ", ".join(entry.technologies))
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


def contact_as_dict(contact: ContactDetails | None) -> dict[str, str] | None:
    if contact is None:
        return None
    payload = contact.model_dump(exclude_none=True)
    return {key: value for key, value in payload.items() if value} or None
