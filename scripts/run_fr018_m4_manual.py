"""FR-018 M4 manual validation helper — parse owner .eml without persisting.

Usage::

    python scripts/run_fr018_m4_manual.py path/to/alert.eml

Prints platform, jobs, and whether EmailAcquisitionAdapter provenance would pass.
Does not write Opportunities (use ``cic opportunity discover-email`` for that).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from career_intelligence.discovery import (
    EmailAcquisitionAdapter,
    assert_email_acquisition_provenance,
    email_locator,
    parse_job_alert_email,
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/run_fr018_m4_manual.py <alert.eml>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        parsed = parse_job_alert_email(path)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    rows = []
    for job in parsed.jobs:
        locator = email_locator(parsed.path, job.index)
        try:
            result = EmailAcquisitionAdapter(locator=locator).acquire()
            assert_email_acquisition_provenance(result)
            rows.append(
                {
                    "index": job.index,
                    "title": result.title,
                    "job_url": str(result.source_url),
                    "source_identifier": result.source_identifier,
                    "acquire": "ok",
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append({"index": job.index, "acquire": "failed", "error": str(exc)})

    print(
        json.dumps(
            {
                "ok": True,
                "platform": parsed.platform,
                "from": parsed.from_addr,
                "subject": parsed.subject,
                "message_id": parsed.message_id,
                "jobs": rows,
            },
            indent=2,
        )
    )
    return 0 if all(r.get("acquire") == "ok" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
