"""Functional coverage for FR-014 M2 technology truth validation."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import TruthValidationService

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

REDWOLF = (
    "Roles centred on Python, TypeScript, and Vue are where I do my best "
    "engineering work. I want to join a team shipping production AI."
)


def _profile() -> CareerProfile:
    base = CareerProfileService.from_path(FIXTURES / "minimal_valid_profile.yaml").load()
    data = base.model_dump(mode="python")
    data["skills"]["technical"].append(
        {"name": "FastAPI", "evidence": "project:example-project"}
    )
    data["projects"][0]["technologies"] = ["Python", "FastAPI"]
    return CareerProfile.model_validate(data)


def test_functional_redwolf_blocked_and_supported_path_passes() -> None:
    service = TruthValidationService()
    profile = _profile()

    failed = service.validate_markdown(
        markdown=REDWOLF,
        profile=profile,
        artefact_kind="cover_letter_markdown",
        gate="generation_advisory",
        context_technology_labels=["Python", "TypeScript", "Vue"],
    )
    assert failed.outcome == "fail"
    blocking = [f for f in failed.findings if f.severity == "blocking"]
    assert {f.claim.object_key for f in blocking} >= {"typescript", "vue"}
    supported = [
        f
        for f in failed.findings
        if f.claim.object_key == "python" and f.evidence_status == "supported"
    ]
    assert supported

    passed = service.validate_markdown(
        markdown=(
            "I have experience with Python and FastAPI. "
            "The role uses TypeScript and Vue."
        ),
        profile=profile,
        gate="post_edit_authoritative",
        context_technology_labels=["TypeScript", "Vue"],
    )
    assert passed.outcome == "pass"
    assert any(f.claim.claim_class == "A" for f in passed.findings)
    assert any(f.claim.claim_class == "B" for f in passed.findings)
