"""Consolidated FR-014 M4 recruiter-document claim-validation journey."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import TruthValidationService

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_m4_extended_claims_are_validated_with_technology_regression() -> None:
    base = CareerProfileService.from_path(FIXTURES / "minimal_valid_profile.yaml").load()
    data = base.model_dump(mode="python")
    data["certifications"] = [{
        "id": "aws-saa", "name": "AWS Certified Solutions Architect",
        "issuer": "AWS", "status": "active",
    }]
    data["skills"]["domain"] = [{
        "name": "financial services", "evidence": "project:example-project",
    }]
    profile = CareerProfile.model_validate(data)
    service = TruthValidationService()

    supported = service.validate_markdown(
        markdown=(
            "I have commercial software engineering experience. "
            "I hold AWS Certified Solutions Architect. "
            "I have experience in financial services. "
            "I have One year of Python experience. I built Example Project."
        ),
        profile=profile,
    )
    assert supported.outcome == "pass"
    assert {item.claim.claim_kind for item in supported.findings} >= {
        "employment", "certification", "domain", "duration", "project_delivery",
    }

    blocked = service.validate_markdown(
        markdown=(
            "I have commercial AI engineering experience. "
            "Roles centred on Python, TypeScript, and Vue are where I do my best engineering work."
        ),
        profile=profile,
        context_technology_labels=["TypeScript", "Vue"],
    )
    assert blocked.outcome == "fail"
    assert {item.claim.object_key for item in blocked.findings if item.severity == "blocking"} >= {
        "commercial_ai_engineering", "typescript", "vue",
    }
