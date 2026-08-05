"""Convert generated CV Markdown into the shared print HTML document.

Preserves owner edits in the Markdown. Reuses ``load_cv_print_css`` and the
same inline Markdown → HTML helpers as the TailoredCv HTML renderer.
"""

from __future__ import annotations

import re

from career_intelligence.cv_generation.errors import CvHtmlRenderError
from career_intelligence.cv_generation.html_renderer import (
    _inline_to_html,
    load_cv_print_css,
)
from career_intelligence.document_rendering.errors import DocumentRenderInputError

_HEADING2 = re.compile(r"^##\s+(.+)$")
_HEADING3 = re.compile(r"^###\s+(.+)$")
_ROLE_LINE = re.compile(r"^\*\*(.+)\*\*\s*$")
_LINK_LINE = re.compile(
    r"^(LinkedIn|Portfolio|GitHub):\s+\[([^\]]+)\]\(([^)]+)\)\s*$",
    re.IGNORECASE,
)
_TECH_LINE = re.compile(r"^\*\*Technologies:\*\*\s*(.+)$", re.IGNORECASE)
_STACK_LINE = re.compile(r"^\*\*Technology Stack:\*\*\s*(.+)$", re.IGNORECASE)
_OVERVIEW = re.compile(r"^\*\*Overview:\*\*\s*(.+)$", re.IGNORECASE)
_HIGHLIGHTS = re.compile(r"^\*\*Engineering Highlights:\*\*\s*$", re.IGNORECASE)
_OUTCOMES = re.compile(r"^\*\*Outcomes:\*\*\s*$", re.IGNORECASE)
_ALSO = re.compile(r"^\*\*Also:\*\*\s*(.+)$", re.IGNORECASE)
_METHOD_CAT = re.compile(r"^\*\*(.+?):\*\*\s*(.+)$")


def render_cv_html_from_markdown(markdown: str, *, title: str | None = None) -> str:
    """Render a complete standalone HTML document from generated CV Markdown."""
    text = markdown.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise DocumentRenderInputError("CV Markdown is empty")
    try:
        body = _render_body(text)
        document_title = title or _document_title(text)
        css = load_cv_print_css()
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            f"  <title>{_esc_title(document_title)}</title>\n"
            "  <style>\n"
            f"{css.rstrip()}\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            f"{body}"
            "</body>\n"
            "</html>\n"
        )
    except (DocumentRenderInputError, CvHtmlRenderError):
        raise
    except Exception as exc:  # noqa: BLE001
        raise CvHtmlRenderError(f"HTML rendering failed: {exc}") from exc


def _document_title(markdown: str) -> str:
    lines = markdown.split("\n")
    name = lines[0][2:].strip() if lines and lines[0].startswith("# ") else "CV"
    for line in lines[1:12]:
        match = _ROLE_LINE.match(line.strip())
        if match:
            return f"{name} — {match.group(1).strip()}"
    return name


def _esc_title(value: str) -> str:
    from html import escape

    return escape(value, quote=True)


def _render_body(markdown: str) -> str:
    lines = markdown.split("\n")
    if not lines or not lines[0].startswith("# "):
        raise DocumentRenderInputError("CV Markdown must start with an H1 full name")
    full_name = lines[0][2:].strip()
    parts: list[str] = [f"<h1>{_inline_to_html(full_name)}</h1>\n", '<hr class="header-rule" />\n']

    index = 1
    # Header block until --- or first ##
    header_lines: list[str] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped == "---" or stripped.startswith("## "):
            break
        if stripped:
            header_lines.append(stripped)
        index += 1
    parts.extend(_render_header_block(header_lines))
    if index < len(lines) and lines[index].strip() == "---":
        index += 1

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        heading = _HEADING2.match(stripped)
        if heading:
            section = heading.group(1).strip()
            index += 1
            section_lines: list[str] = []
            while index < len(lines):
                nxt = lines[index].strip()
                if nxt.startswith("## "):
                    break
                section_lines.append(lines[index])
                index += 1
            parts.extend(_render_section(section, section_lines))
            continue
        # Orphan line before any section — treat as paragraph.
        parts.append(f"<p>{_inline_to_html(stripped)}</p>\n")
        index += 1

    return "".join(parts)


def _render_header_block(lines: list[str]) -> list[str]:
    parts: list[str] = []
    role: str | None = None
    for line in lines:
        link = _LINK_LINE.match(line)
        if link:
            label = link.group(1)
            url = link.group(3).strip()
            display = _compact_url(url)
            parts.append(
                f'<p class="contact"><strong>{label}:</strong> '
                f'<a href="{_esc_attr(url)}">{_esc(display)}</a></p>\n'
            )
            continue
        role_match = _ROLE_LINE.match(line)
        if role_match and " · " not in line and "mailto:" not in line:
            role = role_match.group(1).strip()
            continue
        # Contact / location line — may contain markdown links and middots.
        parts.append(f'<p class="contact">{_inline_to_html(_normalize_middot(line))}</p>\n')
    if role:
        parts.append(f'<p class="role">{_inline_to_html(role)}</p>\n')
    return parts


def _render_section(name: str, lines: list[str]) -> list[str]:
    folded = name.casefold()
    if folded == "professional summary":
        return _section_paragraphs(name, lines)
    if folded == "selected engineering highlights":
        return _section_list(name, lines)
    if folded == "core skills":
        return _section_skills(name, lines)
    if folded == "professional experience":
        return _section_experience(name, lines)
    if folded.startswith("featured"):
        return _section_projects(name, lines)
    if "methodology" in folded:
        return _section_methodology(name, lines)
    if folded == "certifications":
        return _section_list(name, lines, wrapper_class="closing")
    return _section_paragraphs(name, lines)


def _section_paragraphs(name: str, lines: list[str]) -> list[str]:
    parts = [f"<h2>{_inline_to_html(name)}</h2>\n"]
    for block in _paragraph_blocks(lines):
        parts.append(f"<p>{_inline_to_html(block)}</p>\n")
    return parts


def _section_list(
    name: str,
    lines: list[str],
    *,
    wrapper_class: str | None = None,
) -> list[str]:
    parts: list[str] = []
    if wrapper_class:
        parts.append(f'<div class="{wrapper_class}">\n')
    parts.append(f"<h2>{_inline_to_html(name)}</h2>\n")
    items = [
        line.strip()[2:].strip()
        for line in lines
        if line.strip().startswith(("- ", "* "))
    ]
    if items:
        parts.append("<ul>\n")
        for item in items:
            parts.append(f"  <li>{_inline_to_html(item)}</li>\n")
        parts.append("</ul>\n")
    if wrapper_class:
        parts.append("</div>\n")
    return parts


def _section_skills(name: str, lines: list[str]) -> list[str]:
    parts = [f"<h2>{_inline_to_html(name)}</h2>\n", '<div class="skills">\n']
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        also = _ALSO.match(stripped)
        if also:
            parts.append(
                f"  <p><strong>Also:</strong> {_inline_to_html(also.group(1).strip())}</p>\n"
            )
        else:
            parts.append(f"  <p>{_inline_to_html(_normalize_middot(stripped))}</p>\n")
    parts.append("</div>\n")
    return parts


def _section_experience(name: str, lines: list[str]) -> list[str]:
    parts = [f"<h2>{_inline_to_html(name)}</h2>\n"]
    blocks = _split_on_heading3(lines)
    for heading, body in blocks:
        parts.append('<div class="experience">\n')
        title = heading.replace(" — ", " — ").replace(" – ", " — ")
        # Markdown uses "Title — Org" or "Title - Org"
        parts.append(f"<h3>{_inline_to_html(title)}</h3>\n")
        meta = None
        highlights: list[str] = []
        technologies = None
        for line in body:
            stripped = line.strip()
            if not stripped:
                continue
            tech = _TECH_LINE.match(stripped)
            if tech:
                technologies = tech.group(1).strip()
                continue
            if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
                meta = stripped.strip("*").strip()
                continue
            if stripped.startswith(("- ", "* ")):
                highlights.append(stripped[2:].strip())
        if meta:
            parts.append(f'<p class="meta">{_inline_to_html(meta)}</p>\n')
        if highlights:
            parts.append("<ul>\n")
            for item in highlights:
                parts.append(f"  <li>{_inline_to_html(item)}</li>\n")
            parts.append("</ul>\n")
        if technologies:
            parts.append(
                f"<p><strong>Technologies:</strong> {_inline_to_html(technologies)}</p>\n"
            )
        parts.append("</div>\n")
    return parts


def _section_projects(name: str, lines: list[str]) -> list[str]:
    parts = [f"<h2>{_inline_to_html(name)}</h2>\n"]
    blocks = _split_on_heading3(lines)
    for heading, body in blocks:
        parts.append('<div class="project">\n')
        parts.append(f"<h3>{_inline_to_html(heading)}</h3>\n")
        mode: str | None = None
        list_items: list[str] = []
        for line in body:
            stripped = line.strip()
            if not stripped:
                if mode in {"highlights", "outcomes"} and list_items:
                    parts.append(_ul(list_items))
                    list_items = []
                continue
            overview = _OVERVIEW.match(stripped)
            if overview:
                if list_items:
                    parts.append(_ul(list_items))
                    list_items = []
                mode = None
                parts.append(
                    f"<p><strong>Overview:</strong> "
                    f"{_inline_to_html(overview.group(1).strip())}</p>\n"
                )
                continue
            if _HIGHLIGHTS.match(stripped):
                if list_items:
                    parts.append(_ul(list_items))
                    list_items = []
                mode = "highlights"
                parts.append("<p><strong>Engineering Highlights:</strong></p>\n")
                continue
            if _OUTCOMES.match(stripped):
                if list_items:
                    parts.append(_ul(list_items))
                    list_items = []
                mode = "outcomes"
                parts.append("<p><strong>Outcomes:</strong></p>\n")
                continue
            stack = _STACK_LINE.match(stripped)
            if stack:
                if list_items:
                    parts.append(_ul(list_items))
                    list_items = []
                mode = None
                parts.append(
                    f'<p class="stack"><strong>Technology Stack:</strong> '
                    f"{_inline_to_html(stack.group(1).strip())}</p>\n"
                )
                continue
            if stripped.startswith(("- ", "* ")):
                list_items.append(stripped[2:].strip())
                continue
            if list_items:
                parts.append(_ul(list_items))
                list_items = []
            mode = None
            parts.append(f"<p>{_inline_to_html(stripped)}</p>\n")
        if list_items:
            parts.append(_ul(list_items))
        parts.append("</div>\n")
    return parts


def _section_methodology(name: str, lines: list[str]) -> list[str]:
    parts = ['<div class="methodology">\n', f"<h2>{_inline_to_html(name)}</h2>\n"]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        cat = _METHOD_CAT.match(stripped)
        if cat and " · " in cat.group(2):
            parts.append(
                f"<p><strong>{_inline_to_html(cat.group(1))}:</strong> "
                f"{_inline_to_html(cat.group(2).strip())}</p>\n"
            )
        else:
            parts.append(f"<p>{_inline_to_html(stripped)}</p>\n")
    parts.append("</div>\n")
    return parts


def _split_on_heading3(lines: list[str]) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_body: list[str] = []
    for line in lines:
        match = _HEADING3.match(line.strip())
        if match:
            if current_heading is not None:
                blocks.append((current_heading, current_body))
            current_heading = match.group(1).strip()
            current_body = []
            continue
        if current_heading is None:
            continue
        current_body.append(line)
    if current_heading is not None:
        blocks.append((current_heading, current_body))
    return blocks


def _paragraph_blocks(lines: list[str]) -> list[str]:
    return [
        block.strip()
        for block in "\n".join(lines).split("\n\n")
        if block.strip() and not block.strip().startswith("## ")
    ]


def _ul(items: list[str]) -> str:
    chunks = ["<ul>\n"]
    for item in items:
        chunks.append(f"  <li>{_inline_to_html(item)}</li>\n")
    chunks.append("</ul>\n")
    return "".join(chunks)


def _normalize_middot(text: str) -> str:
    # Generated Markdown may use a middot or a mojibake stand-in.
    return (
        text.replace(" · ", " · ")
        .replace(" A� ", " · ")
        .replace(" â€¢ ", " · ")
    )


def _compact_url(url: str) -> str:
    display = url.strip()
    for prefix in ("https://", "http://"):
        if display.casefold().startswith(prefix):
            display = display[len(prefix) :]
            break
    if display.casefold().startswith("www."):
        display = display[4:]
    return display.rstrip("/") or url


def _esc(value: str) -> str:
    from html import escape

    return escape(value, quote=False)


def _esc_attr(value: str) -> str:
    from html import escape

    return escape(value, quote=True)
