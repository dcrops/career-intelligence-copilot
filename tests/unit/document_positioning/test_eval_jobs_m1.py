"""M1 inspection of the four frozen evaluation jobs — not production generation."""

from __future__ import annotations

from career_intelligence.document_positioning import SupportStatus, build_positioning_plan

from tests.unit.document_positioning.helpers import (
    csk_job_analysis,
    golden_job_analysis,
    live_profile,
)


def _build(stem: str | None = None, *, csk: bool = False):
    profile = live_profile()
    job = csk_job_analysis() if csk else golden_job_analysis(stem or "")
    return build_positioning_plan(job, profile)


def test_e1_allura_is_ai_lead_applied_control() -> None:
    plan = _build("001_strong_ai_engineer")
    assert plan.trajectory_mode == "ai_lead"
    python = next(
        item
        for item in plan.employer_needs
        if item.need.label.casefold() == "python"
    )
    assert python.classification.status is SupportStatus.SUPPORTED_DIRECT


def test_e2_csk_mixed_fit_related_bedrock_direct_rag_chatbot_gap() -> None:
    plan = _build(csk=True)
    by_label = {item.need.label.casefold(): item for item in plan.employer_needs}
    assert by_label["rag"].classification.status is SupportStatus.SUPPORTED_DIRECT
    bedrock = by_label["aws bedrock"]
    assert bedrock.classification.status is SupportStatus.SUPPORTED_RELATED
    assert bedrock.classification.promotable_profile_label == "AWS"
    assert bedrock.classification.may_claim_requested is False
    chatbot = next(
        item
        for item in plan.employer_needs
        if item.classification.requested_identity == "chatbot"
    )
    assert chatbot.classification.status is SupportStatus.UNSUPPORTED
    assert plan.trajectory_mode == "ai_lead"
    forbidden = {claim.may_not_claim.casefold() for claim in plan.forbidden_claims}
    assert "bedrock" in forbidden


def test_e3_maincode_stretch_does_not_invent_gpu_employment() -> None:
    plan = _build("012_maincode_ai_infrastructure_engineer")
    gpu = next(
        item for item in plan.employer_needs if item.need.label.casefold() == "gpu"
    )
    assert gpu.classification.status is SupportStatus.UNSUPPORTED
    assert gpu.evidence_refs == ()
    assert plan.trajectory_mode == "ai_lead"
    assert not any(
        claim.kind == "direct" and "gpu" in claim.statement.casefold()
        for claim in plan.argument_spine
    )


def test_e4_repurpose_uses_full_chapters() -> None:
    plan = _build("008_repurpose_it_ai_adoption_specialist")
    assert plan.trajectory_mode == "full_chapters"


def test_four_jobs_produce_distinct_positioning() -> None:
    e1 = _build("001_strong_ai_engineer")
    e2 = _build(csk=True)
    e3 = _build("012_maincode_ai_infrastructure_engineer")
    e4 = _build("008_repurpose_it_ai_adoption_specialist")
    dumps = [
        plan.model_dump(mode="json") for plan in (e1, e2, e3, e4)
    ]
    encoded = [str(item) for item in dumps]
    assert len(set(encoded)) == 4
    assert e4.trajectory_mode != e1.trajectory_mode
    assert any(
        item.classification.status is SupportStatus.SUPPORTED_RELATED
        for item in e2.employer_needs
    )
    assert not any(
        item.classification.status is SupportStatus.SUPPORTED_RELATED
        for item in e3.employer_needs
    )
