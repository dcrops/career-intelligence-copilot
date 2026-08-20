#!/usr/bin/env python3
"""Run the Document Positioning M5 frozen quality benchmark.

Default: live OpenAI composers for CIC (M3/M4) and the strong baseline.
Does not wire ``cic package prepare``. Does not regenerate the CSK live
package. Does not run SEEK, Playwright, or AAS. Does not reveal the A/B
mapping.

  python scripts/run_m5_benchmark.py
  python scripts/run_m5_benchmark.py --offline-fixtures
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from career_intelligence.document_positioning.benchmark.run import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    BenchmarkBlockedError,
    load_openai_api_key,
    run_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline-fixtures",
        action="store_true",
        help="Use pack-faithful fixture composers. Not the quality candidate.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Benchmark output directory (owner_review + hidden records).",
    )
    args = parser.parse_args()
    live = not args.offline_fixtures
    if live:
        key = load_openai_api_key(_REPO_ROOT)
        if not key:
            print(
                "OPENAI_API_KEY is not set (environment or config/local_secrets.env). "
                "M5 quality generation requires live OpenAI. Pass --offline-fixtures "
                "only to exercise the harness.",
                file=sys.stderr,
            )
            return 2
        os.environ["OPENAI_API_KEY"] = key
        print(
            "Running live M5 generation (CIC bounded composers + strong baseline). "
            "Mapping will remain hidden."
        )
    else:
        print("Running offline fixture harness. Not the M5 quality candidate.")
    try:
        result = run_benchmark(args.output_dir, live=live)
    except BenchmarkBlockedError as error:
        print(f"M5 BENCHMARK BLOCKED — {error}", file=sys.stderr)
        return 1
    print(f"owner_review: {result['owner_dir']}")
    print(f"hidden records: {result['hidden_dir']}")
    print("M5 READY FOR OWNER BLIND REVIEW")
    print("Do not open hidden/ab_mapping.json until scoring is complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
