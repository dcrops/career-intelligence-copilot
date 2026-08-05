#!/usr/bin/env python3
"""Manual validation for FR-014 M2 truth validation (technology claims).

Examples:
  python scripts/run_fr014_truth_manual.py
  python scripts/run_fr014_truth_manual.py --profile data/career_profile.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from career_intelligence.profile import CareerProfileService
from career_intelligence.truth_validation import TruthValidationService

REDWOLF = (
    "Roles centred on Python, TypeScript, and Vue are where I do my best "
    "engineering work."
)
SUPPORTED = "I have experience with Python and FastAPI in production services."
EMPLOYER = "The role uses TypeScript and Vue extensively."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        type=Path,
        default=_REPO_ROOT / "tests" / "fixtures" / "minimal_valid_profile.yaml",
        help="Career profile YAML path",
    )
    args = parser.parse_args()

    profile = CareerProfileService.from_path(args.profile).load()
    # Ensure FastAPI exists for the supported demo when using minimal fixture.
    if args.profile.name == "minimal_valid_profile.yaml":
        data = profile.model_dump(mode="python")
        if not any(s["name"] == "FastAPI" for s in data["skills"]["technical"]):
            data["skills"]["technical"].append(
                {"name": "FastAPI", "evidence": "project:example-project"}
            )
            data["projects"][0]["technologies"] = ["Python", "FastAPI"]
            from career_intelligence.profile.models import CareerProfile

            profile = CareerProfile.model_validate(data)

    service = TruthValidationService()
    catalogue = service.build_catalogue(profile)
    print(f"catalogue_entries={len(catalogue.entries)} id={catalogue.catalogue_id}")

    cases = [
        ("redwolf", REDWOLF, ["Python", "TypeScript", "Vue"], "fail"),
        ("supported", SUPPORTED, None, "pass"),
        ("employer_context", EMPLOYER, ["TypeScript", "Vue"], "pass"),
    ]
    all_ok = True
    for name, markdown, context, expected in cases:
        report = service.validate_markdown(
            markdown=markdown,
            catalogue=catalogue,
            context_technology_labels=context,
        )
        ok = report.outcome == expected
        all_ok = all_ok and ok
        print(
            f"[{name}] outcome={report.outcome} expected={expected} "
            f"findings={len(report.findings)} ok={ok}"
        )
        print(f"  summary: {report.summary}")
        for finding in report.findings:
            print(
                f"  - {finding.claim.object_key} class={finding.claim.claim_class} "
                f"detection={finding.detection_certainty} "
                f"evidence={finding.evidence_status} severity={finding.severity}"
            )

    # Emit one full Redwolf report for inspection
    redwolf = service.validate_markdown(
        markdown=REDWOLF,
        catalogue=catalogue,
        context_technology_labels=["Python", "TypeScript", "Vue"],
    )
    out = _REPO_ROOT / "data" / "_fr014_m2_manual"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "redwolf_report.json"
    path.write_text(
        json.dumps(redwolf.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    print(f"wrote {path}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
