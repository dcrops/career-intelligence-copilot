"""FR-018 M3 manual live validation — production UrllibHttpClient (no persist).

Usage (from repo root)::

    python scripts/run_fr018_m3_manual.py

Does not write Opportunities. Does not use Playwright.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from career_intelligence.discovery import (
    DiscoveryUnsupportedSourceError,
    UrlAcquisitionAdapter,
    UrllibHttpClient,
    assert_url_acquisition_provenance,
    classify_supported_job_url,
)

URLS = [
    ("SEEK", "https://www.seek.com.au/job/93312273"),
    ("LINKEDIN", "https://www.linkedin.com/jobs/view/4429615445"),
    (
        "LINKEDIN_SLUG",
        "https://au.linkedin.com/jobs/view/senior-ai-engineer-at-fyndr-group-4429615445",
    ),
    ("INDEED", "https://au.indeed.com/viewjob?jk=6449f2b22e094d45"),
    ("CAREERS", "https://www.thoughtworks.com/careers/jobs/7920279"),
]


def main() -> int:
    client = UrllibHttpClient()
    rows: list[dict[str, object]] = []
    for label, url in URLS:
        row: dict[str, object] = {"label": label, "url": url}
        try:
            ref = classify_supported_job_url(url)
            row["classify"] = {
                "platform": ref.platform,
                "platform_job_id": ref.platform_job_id,
                "canonical_url": ref.canonical_url,
            }
        except DiscoveryUnsupportedSourceError as exc:
            row["classify"] = "unsupported_source"
            row["failure"] = str(exc)
            rows.append(row)
            print(label, "UNSUPPORTED", exc)
            continue
        try:
            result = UrlAcquisitionAdapter(
                url=url, client=client, timeout_seconds=30.0
            ).acquire()
            assert_url_acquisition_provenance(result)
            row["acquire"] = "ok"
            row["title"] = result.title
            row["company"] = result.company
            row["raw_len"] = len(result.raw_content)
            row["source_identifier"] = result.source_identifier
            print(label, "OK", result.title, len(result.raw_content))
        except Exception as exc:  # noqa: BLE001
            row["acquire"] = "failed"
            row["failure"] = getattr(exc, "detail", None) or str(exc)
            print(label, "FAIL", row["failure"])
        rows.append(row)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "client": "UrllibHttpClient+truststore",
        "results": rows,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
