#!/usr/bin/env python3
"""Render an Engineering Learning Academy Masterclass Markdown to PDF.

Official study edition. Does not rewrite Masterclass content — formatting only.

Usage:
  python scripts/render_masterclass_pdf.py docs/masterclass/FR017/Engineering_Masterclass_002_FR017.md

Requires: weasyprint (project dependency), markdown (pip install markdown).
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


def _parse_meta(md: str) -> dict[str, str]:
    """Extract Lean Masterclass header fields from the Markdown body."""
    meta: dict[str, str] = {
        "document_title": "Engineering Masterclass",
        "work_title": "",
        "subtitle": "",
        "edition": "Engineering Learning Academy — Lean Edition",
        "status": "",
        "audience": "",
        "functional_requirement": "",
    }
    lines = md.splitlines()
    for line in lines[:40]:
        if line.startswith("# "):
            meta["document_title"] = line[2:].strip()
        elif line.startswith("## ") and not meta["work_title"]:
            meta["work_title"] = line[3:].strip()
            m = re.search(r"(FR-\d+)\s+(.+)$", meta["work_title"])
            if m:
                meta["functional_requirement"] = f"{m.group(1)} — {m.group(2).strip()}"
            else:
                m2 = re.search(r"(FR-\d+)\b", meta["work_title"])
                if m2:
                    meta["functional_requirement"] = m2.group(1)
        elif line.startswith("**Subtitle:**"):
            meta["subtitle"] = line.split(":**", 1)[1].strip().rstrip(" *")
        elif line.startswith("**Edition:**"):
            meta["edition"] = line.split(":**", 1)[1].strip().rstrip(" *")
        elif line.startswith("**Status:**"):
            meta["status"] = line.split(":**", 1)[1].strip().rstrip(" *")
        elif line.startswith("**Audience:**"):
            meta["audience"] = line.split(":**", 1)[1].strip().rstrip(" *")
    return meta


def _strip_leading_titles(md: str) -> str:
    """Remove H1/H2 and metadata bullets already shown on the title page."""
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            line.startswith("# ")
            or line.startswith("## ")
            or line.startswith("**Subtitle:**")
            or line.startswith("**Edition:**")
            or line.startswith("**Status:**")
            or line.startswith("**Audience:**")
            or line.startswith("**Source package:**")
            or line.strip() == "---"
            or line.strip() == ""
        ):
            i += 1
            continue
        break
    return "\n".join(lines[i:]).lstrip("\n")


def _build_document(meta: dict[str, str], body_html: str, toc_html: str) -> str:
    def esc(key: str) -> str:
        return html.escape(meta.get(key, "") or "")

    toc_block = ""
    if toc_html.strip():
        toc_block = f"""
<section class="toc page-break-after">
  <h1>Contents</h1>
  {toc_html}
</section>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{esc("document_title")}</title>
<style>
  @page {{
    size: A4;
    margin: 22mm 18mm 24mm 18mm;
    @bottom-center {{
      content: counter(page);
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      font-size: 9pt;
      color: #555;
    }}
    @bottom-left {{
      content: "Engineering Learning Academy";
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      font-size: 8pt;
      color: #888;
    }}
    @bottom-right {{
      content: "{esc("document_title")}";
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      font-size: 8pt;
      color: #888;
    }}
  }}
  @page :first {{
    @bottom-center {{ content: none; }}
    @bottom-left {{ content: none; }}
    @bottom-right {{ content: none; }}
  }}

  :root {{
    --ink: #1a1a1a;
    --muted: #555;
    --rule: #d0d0d0;
    --code-bg: #f4f4f5;
    --accent: #1f3a5f;
  }}

  html, body {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: var(--ink);
  }}

  .title-page {{
    page-break-after: always;
    min-height: 240mm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 18mm 8mm;
  }}
  .title-page .eyebrow {{
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 9pt;
    color: var(--muted);
    margin-bottom: 18mm;
  }}
  .title-page h1 {{
    font-size: 26pt;
    line-height: 1.15;
    margin: 0 0 8mm 0;
    color: var(--accent);
    font-weight: 650;
  }}
  .title-page .work-title {{
    font-size: 14pt;
    margin: 0 0 6mm 0;
    font-weight: 600;
  }}
  .title-page .subtitle {{
    font-size: 12pt;
    color: var(--muted);
    margin: 0 0 14mm 0;
    max-width: 140mm;
  }}
  .meta-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8mm;
  }}
  .meta-table th, .meta-table td {{
    text-align: left;
    vertical-align: top;
    padding: 2.2mm 3mm 2.2mm 0;
    border-bottom: 1px solid var(--rule);
    font-size: 10pt;
  }}
  .meta-table th {{
    width: 42mm;
    color: var(--muted);
    font-weight: 600;
  }}
  .title-page .footer-note {{
    margin-top: auto;
    padding-top: 20mm;
    font-size: 9pt;
    color: var(--muted);
  }}

  .page-break-after {{ page-break-after: always; }}

  .toc h1 {{
    font-size: 18pt;
    color: var(--accent);
    margin-top: 0;
  }}
  .toc ul {{
    list-style: none;
    padding-left: 0;
  }}
  .toc ul ul {{
    padding-left: 5mm;
  }}
  .toc a {{
    color: var(--ink);
    text-decoration: none;
  }}
  .toc li {{
    margin: 1.6mm 0;
  }}

  .body h1, .body h2, .body h3, .body h4 {{
    color: var(--accent);
    page-break-after: avoid;
  }}
  .body h1 {{ font-size: 18pt; margin-top: 0; }}
  .body h2 {{ font-size: 14pt; margin-top: 8mm; border-bottom: 1px solid var(--rule); padding-bottom: 1.5mm; }}
  .body h3 {{ font-size: 12pt; margin-top: 6mm; }}
  .body h4 {{ font-size: 11pt; margin-top: 4mm; }}

  .body p {{ margin: 2.5mm 0; }}
  .body ul, .body ol {{ margin: 2mm 0 3mm 0; padding-left: 6mm; }}
  .body li {{ margin: 1mm 0; }}
  .body blockquote {{
    margin: 3mm 0;
    padding: 2mm 4mm;
    border-left: 3px solid var(--accent);
    color: #333;
    background: #fafafa;
  }}
  .body hr {{
    border: none;
    border-top: 1px solid var(--rule);
    margin: 6mm 0;
  }}
  .body strong {{ font-weight: 650; }}

  .body table {{
    width: 100%;
    border-collapse: collapse;
    margin: 3mm 0 5mm 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
  }}
  .body th, .body td {{
    border: 1px solid #ccc;
    padding: 1.8mm 2.2mm;
    text-align: left;
    vertical-align: top;
  }}
  .body th {{
    background: #eef2f6;
    font-weight: 650;
  }}

  .body pre {{
    background: var(--code-bg);
    border: 1px solid #e0e0e0;
    border-radius: 2px;
    padding: 3mm 3.5mm;
    font-size: 8.5pt;
    line-height: 1.35;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
    page-break-inside: avoid;
  }}
  .body code {{
    font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
    font-size: 8.8pt;
    background: var(--code-bg);
    padding: 0.2mm 1mm;
  }}
  .body pre code {{
    background: transparent;
    padding: 0;
    font-size: 8.5pt;
  }}
</style>
</head>
<body>
<section class="title-page">
  <div class="eyebrow">Engineering Learning Academy</div>
  <h1>{esc("document_title")}</h1>
  <p class="work-title">{esc("work_title")}</p>
  <p class="subtitle">{esc("subtitle")}</p>
  <table class="meta-table">
    <tr><th>Functional Requirement</th><td>{esc("functional_requirement")}</td></tr>
    <tr><th>Edition</th><td>{esc("edition")}</td></tr>
    <tr><th>Status</th><td>{esc("status")}</td></tr>
    <tr><th>Audience</th><td>{esc("audience")}</td></tr>
    <tr><th>Document type</th><td>Official study edition (PDF)</td></tr>
  </table>
  <p class="footer-note">Faithful rendering of the Lean Engineering Masterclass Markdown.
Canonical engineering remains the FR acceptance report and ADR.</p>
</section>
{toc_block}
<section class="body">
{body_html}
</section>
</body>
</html>
"""


def render_masterclass_pdf(md_path: Path, pdf_path: Path | None = None) -> Path:
    md_text = md_path.read_text(encoding="utf-8")
    meta = _parse_meta(md_text)
    body_md = _strip_leading_titles(md_text)

    # markdown TOC extension injects [TOC] when present; build separately.
    import markdown
    from markdown.extensions.toc import TocExtension

    md_converter = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "sane_lists",
            "smarty",
            TocExtension(toc_depth="3-3", permalink=False, title=""),
        ],
        output_format="html5",
    )
    body_html = md_converter.convert(body_md)
    toc_html = getattr(md_converter, "toc", "") or ""

    document = _build_document(meta, body_html, toc_html)

    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Missing dependency: weasyprint") from exc

    out = pdf_path or md_path.with_suffix(".pdf")
    HTML(string=document, base_url=str(md_path.parent.resolve())).write_pdf(out)
    if not out.is_file() or out.read_bytes()[:4] != b"%PDF":
        raise SystemExit(f"PDF render failed: {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "markdown",
        type=Path,
        help="Path to Engineering_Masterclass_*.md",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: same stem as Markdown)",
    )
    args = parser.parse_args(argv)
    md_path = args.markdown
    if not md_path.is_file():
        print(f"Markdown not found: {md_path}", file=sys.stderr)
        return 1
    out = render_masterclass_pdf(md_path, args.output)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
