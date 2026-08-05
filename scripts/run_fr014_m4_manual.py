#!/usr/bin/env python3
"""Manual matrix for FR-014 M4 deterministic extended claim validation.

Usage: python scripts/run_fr014_m4_manual.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import TruthValidationService


def _with(**changes: object) -> CareerProfile:
    base = CareerProfileService.from_path(
        _ROOT / "tests" / "fixtures" / "minimal_valid_profile.yaml"
    ).load()
    data = base.model_dump(mode="python")
    data.update(changes)
    return CareerProfile.model_validate(data)


def main() -> int:
    minimal = CareerProfileService.from_path(
        _ROOT / "tests" / "fixtures" / "minimal_valid_profile.yaml"
    ).load()
    service = TruthValidationService()

    independent = _with(
        experience=[
            {
                "id": "indie",
                "kind": "independent_engineering",
                "organisation": "Self",
                "title": "Independent Engineer",
                "start_date": "2024-01",
                "end_date": "2025-01",
                "location": "Melbourne",
                "highlights": ["Built client systems."],
                "technologies": ["Python"],
            }
        ]
    )
    certified = _with(
        certifications=[
            {
                "id": "aws-saa",
                "name": "AWS Certified Solutions Architect",
                "issuer": "AWS",
                "status": "active",
            }
        ],
        skills={
            "technical": [{"name": "Python", "evidence": "experience:example-role"}],
            "domain": [
                {"name": "financial services", "evidence": "project:example-project"}
            ],
            "soft": [],
        },
    )

    matrix: list[tuple[str, str, CareerProfile, str]] = [
        (
            "commercial AI unsupported",
            "I have commercial AI engineering experience.",
            minimal,
            "fail",
        ),
        (
            "commercial software supported",
            "I have commercial software engineering experience.",
            minimal,
            "pass",
        ),
        (
            "independent engineering supported",
            "I have independent engineering experience.",
            independent,
            "pass",
        ),
        (
            "certification present",
            "I hold AWS Certified Solutions Architect.",
            certified,
            "pass",
        ),
        (
            "certification absent",
            "I hold AWS Certified Solutions Architect.",
            minimal,
            "fail",
        ),
        (
            "years supported",
            "I have One year of Python experience.",
            minimal,
            "pass",
        ),
        (
            "years overclaim",
            "I have Ten years of Python experience.",
            minimal,
            "fail",
        ),
        (
            "years ambiguous",
            "I have Two years of Quantum capability.",
            minimal,
            "review_required",
        ),
        (
            "delivery supported",
            "I built Example Project.",
            minimal,
            "pass",
        ),
        (
            "delivery unresolved",
            "I built the Redwolf Platform.",
            minimal,
            "review_required",
        ),
        (
            "domain supported",
            "I have experience in financial services.",
            certified,
            "pass",
        ),
        (
            "domain unsupported",
            "I have experience in healthcare.",
            certified,
            "fail",
        ),
        (
            "redwolf technology regression",
            "Roles centred on Python, TypeScript, and Vue are where I do my best "
            "engineering work.",
            minimal,
            "fail",
        ),
    ]

    for name, markdown, profile, expected in matrix:
        report = service.validate_markdown(
            markdown=markdown,
            profile=profile,
            context_technology_labels=["TypeScript", "Vue"],
        )
        print(f"{name}: {report.outcome} (expected {expected})")
        assert report.outcome == expected, (name, report.outcome, report.summary)
    print("M4 MANUAL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
