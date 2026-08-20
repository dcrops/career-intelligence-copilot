"""M2 inspection of frozen E1–E4 jobs through catalogue-backed TailoringPlan."""

from __future__ import annotations

from career_intelligence.cv_generation import (
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
)
from career_intelligence.document_positioning import SupportStatus, build_positioning_plan
from tests.unit.cv_generation.helpers import strategy_from_payload
from tests.unit.document_positioning.helpers import (
    csk_job_analysis,
    golden_job_analysis,
    live_profile,
)

_PLANNER_STATUS = {
    "supported": SupportStatus.SUPPORTED_DIRECT,
    "related": SupportStatus.SUPPORTED_RELATED,
    "unsupported": SupportStatus.UNSUPPORTED,
}


def _tailoring(job):
    return TailoringPlanService(DeterministicTailoringPlanner()).plan(
        strategy_from_payload(job_analysis=job),
        live_profile(),
        options=TailoringOptions(owner_approved_to_tailor=True),
    )


def _tech_priority(plan, label: str):
    return next(
        item
        for item in plan.jd_priorities
        if item.kind == "technology" and item.label.casefold() == label.casefold()
    )


def _assert_shared_technology_agreement(job) -> None:
    profile = live_profile()
    positioning = build_positioning_plan(job, profile)
    tailoring = _tailoring(job)
    by_label = {
        item.label.casefold(): item
        for item in tailoring.jd_priorities
        if item.kind == "technology"
    }
    for need in positioning.employer_needs:
        if need.need.kind != "technology":
            continue
        priority = by_label[need.need.label.casefold()]
        assert _PLANNER_STATUS[priority.candidate_support] is need.classification.status
        if need.classification.status is SupportStatus.SUPPORTED_RELATED:
            assert priority.may_claim_requested is False
            assert (
                priority.related_profile_capability
                == need.classification.promotable_profile_label
            )


def test_e1_allura_python_rest_llm_direct_without_invented_cloud() -> None:
    job = golden_job_analysis("001_strong_ai_engineer")
    plan = _tailoring(job)
    assert _tech_priority(plan, "Python").candidate_support == "supported"
    assert _tech_priority(plan, "REST APIs").candidate_support == "supported"
    llm = _tech_priority(plan, "LLM")
    assert llm.candidate_support == "supported"
    assert llm.related_profile_capability == "LLM application development"
    assert llm.may_claim_requested is True
    assert _tech_priority(plan, "Google Cloud").candidate_support == "unsupported"
    assert _tech_priority(plan, "MLOps").candidate_support == "unsupported"
    assert _tech_priority(plan, "DevOps").candidate_support == "unsupported"
    promoted = {item.skill_name.casefold() for item in plan.skills_to_promote}
    assert "google cloud" not in promoted
    assert "mlops" not in promoted
    assert "devops" not in promoted
    _assert_shared_technology_agreement(job)


def test_e2_csk_rag_direct_bedrock_related_chatbot_gap() -> None:
    job = csk_job_analysis()
    plan = _tailoring(job)
    assert _tech_priority(plan, "RAG").candidate_support == "supported"
    bedrock = _tech_priority(plan, "AWS Bedrock")
    assert bedrock.candidate_support == "related"
    assert bedrock.related_profile_capability == "AWS"
    assert bedrock.may_claim_requested is False
    chatbot = next(
        item
        for item in build_positioning_plan(job, live_profile()).employer_needs
        if item.classification.requested_identity == "chatbot"
    )
    assert chatbot.classification.status is SupportStatus.UNSUPPORTED
    promoted = {item.skill_name.casefold() for item in plan.skills_to_promote}
    assert "aws bedrock" not in promoted
    assert "bedrock" not in promoted
    assert not any("chatbot" in name for name in promoted)
    _assert_shared_technology_agreement(job)


def test_e3_maincode_does_not_invent_gpu_linux_hpc() -> None:
    job = golden_job_analysis("012_maincode_ai_infrastructure_engineer")
    plan = _tailoring(job)
    for label in ("GPU", "Linux", "HPC"):
        try:
            priority = _tech_priority(plan, label)
        except StopIteration:
            continue
        assert priority.candidate_support == "unsupported"
        assert priority.label.casefold() not in {
            item.skill_name.casefold() for item in plan.skills_to_promote
        }
    _assert_shared_technology_agreement(job)


def test_e4_repurpose_copilot_claude_remain_gaps() -> None:
    job = golden_job_analysis("008_repurpose_it_ai_adoption_specialist")
    plan = _tailoring(job)
    positioning = build_positioning_plan(job, live_profile())
    assert positioning.trajectory_mode == "full_chapters"
    promoted = {item.skill_name.casefold() for item in plan.skills_to_promote}
    for label in ("Copilot", "Claude", "GitHub Copilot"):
        try:
            priority = _tech_priority(plan, label)
        except StopIteration:
            continue
        assert priority.candidate_support == "unsupported"
        assert label.casefold() not in promoted
    assert "copilot" not in promoted
    assert "claude" not in promoted
    _assert_shared_technology_agreement(job)
