#!/usr/bin/env python3
"""Inject canonical CV print CSS into the standalone Master CV HTML."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from career_intelligence.cv_generation.css_sync import (  # noqa: E402
    default_master_cv_html_path,
    master_html_uses_canonical_css,
    sync_master_cv_html,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Master CV HTML path (default: career-documents/cv/master_ai_engineer_cv.html)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if Master HTML CSS differs from assets/cv_print.css",
    )
    args = parser.parse_args(argv)
    path = args.path or default_master_cv_html_path(_REPO_ROOT)
    if args.check:
        html = path.read_text(encoding="utf-8")
        if master_html_uses_canonical_css(html):
            print(f"OK: {path} embeds canonical cv_print.css")
            return 0
        print(f"OUT OF SYNC: {path} does not match assets/cv_print.css", file=sys.stderr)
        return 1
    synced = sync_master_cv_html(path)
    print(f"Synced canonical CSS into {synced}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
