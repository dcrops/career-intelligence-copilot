#!/usr/bin/env python3
"""Render-only: existing generated Markdown → HTML → PDF.

This is NOT document generation. It does not run Job Analysis, Opportunity
Assessment, Portfolio Match, Application Strategy, planners, composers, or
OpenAI. It only reuses the existing HTML/CSS and WeasyPrint PDF renderers.

Examples:
  python scripts/render_document.py \\
      --markdown career-documents/cover-letters/generated/example.md

  python scripts/render_document.py \\
      --markdown career-documents/cv/generated/example.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from career_intelligence.document_rendering import (
    DocumentRenderError,
    DocumentRenderHtmlError,
    DocumentRenderInputError,
    DocumentRenderPdfError,
    UnsupportedDocumentTypeError,
    render_document_from_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render HTML and PDF from an existing generated Markdown draft "
            "(render-only; does not regenerate content)."
        )
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        required=True,
        help="Path to an existing CV or cover-letter Markdown draft.",
    )
    parser.add_argument(
        "--kind",
        choices=("cover_letter", "cv"),
        default=None,
        help="Optional override when path/content detection is ambiguous.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = render_document_from_markdown(
            args.markdown,
            kind=args.kind,
        )
    except DocumentRenderInputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except UnsupportedDocumentTypeError as exc:
        print(f"Unsupported document: {exc}", file=sys.stderr)
        return 2
    except DocumentRenderHtmlError as exc:
        print(f"HTML render failed: {exc}", file=sys.stderr)
        return 1
    except DocumentRenderPdfError as exc:
        print(f"PDF render failed: {exc}", file=sys.stderr)
        return 1
    except DocumentRenderError as exc:
        print(f"Render failed: {exc}", file=sys.stderr)
        return 1

    print(f"kind: {result.kind}")
    print(f"markdown (unchanged): {result.markdown_path}")
    print(f"html: {result.html_path}")
    print(f"pdf: {result.pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
