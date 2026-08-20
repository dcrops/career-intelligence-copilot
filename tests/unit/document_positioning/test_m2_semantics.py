"""M2 semantic regression: catalogue identities in the live TailoringPlan planner."""

from __future__ import annotations

from career_intelligence.cv_generation.deterministic_planner import (
    DeterministicTailoringPlanner,
    _classify_against_profile,
)
from career_intelligence.cv_generation.options import TailoringOptions
from career_intelligence.document_positioning import (
    SupportStatus,
    build_positioning_plan,
    classify_requirement,
    resolve_identity,
)
from career_intelligence.profile.models import Skill
from tests.unit.cv_generation.helpers import (
    make_plan,
    minimal_profile,
    strategy_from_payload,
)
from tests.unit.document_positioning.helpers import (
    analysis_with,
    specialist_job,
    specialist_profile,
    tech,
)

_PLANNER_STATUS = {
    "supported": SupportStatus.SUPPORTED_DIRECT,
    "related": SupportStatus.SUPPORTED_RELATED,
    "unsupported": SupportStatus.UNSUPPORTED,
}


def _plan_for(job, profile):
    return make_plan(profile=profile, strategy=strategy_from_payload(job_analysis=job))


def _priority(plan, label: str):
    return next(item for item in plan.jd_priorities if item.label.casefold() == label.casefold())


def _promoted_names(plan) -> list[str]:
    return [item.skill_name for item in plan.skills_to_promote]


def test_a_rag_aliases_share_one_identity() -> None:
    aliases = (
        "RAG",
        "Retrieval-Augmented Generation",
        "retrieval augmented generation",
    )
    assert {resolve_identity(alias) for alias in aliases} == {"rag"}


def test_b_profile_rag_and_jd_rag_are_direct() -> None:
    result = classify_requirement("RAG", ["Retrieval-Augmented Generation"])
    assert result.status is SupportStatus.SUPPORTED_DIRECT
    assert result.may_claim_requested is True
    support, matched = _classify_against_profile(
        "RAG",
        ["Retrieval-Augmented Generation", "Python"],
    )
    assert support == "supported"
    assert matched == "Retrieval-Augmented Generation"


def test_c_aws_and_bedrock_request_are_related() -> None:
    result = classify_requirement("AWS Bedrock", ["AWS"])
    assert result.status is SupportStatus.SUPPORTED_RELATED
    assert result.requested_identity == "aws_bedrock"
    assert result.promotable_identity == "aws"
    assert result.may_claim_requested is False


def test_d_related_bedrock_does_not_promote_requested_skill() -> None:
    profile = specialist_profile()
    plan = _plan_for(specialist_job(), profile)
    bedrock = _priority(plan, "AWS Bedrock")
    assert bedrock.candidate_support == "related"
    assert bedrock.related_profile_capability == "AWS"
    assert bedrock.may_claim_requested is False
    assert bedrock.requested_capability_identity == "aws_bedrock"
    promoted = {name.casefold() for name in _promoted_names(plan)}
    assert "aws" in promoted
    assert "aws bedrock" not in promoted
    assert "bedrock" not in promoted


def test_e_direct_bedrock_evidence_is_direct() -> None:
    profile = specialist_profile()
    technical = list(profile.skills.technical) + [
        Skill(name="AWS Bedrock", evidence="experience:nbn-de")
    ]
    profile = profile.model_copy(
        update={"skills": profile.skills.model_copy(update={"technical": technical})}
    )
    job = analysis_with(technologies=[tech("AWS Bedrock")])
    plan = _plan_for(job, profile)
    bedrock = _priority(plan, "AWS Bedrock")
    assert bedrock.candidate_support == "supported"
    assert bedrock.may_claim_requested is True
    assert "AWS Bedrock" in _promoted_names(plan)


def test_f_java_does_not_imply_javascript() -> None:
    java_from_js = classify_requirement("Java", ["JavaScript"])
    js_from_java = classify_requirement("JavaScript", ["Java"])
    assert java_from_js.status is SupportStatus.UNSUPPORTED
    assert js_from_java.status is SupportStatus.UNSUPPORTED
    support, _ = _classify_against_profile("Java", ["JavaScript"])
    assert support == "unsupported"


def test_g_rag_does_not_imply_chatbot() -> None:
    result = classify_requirement("chatbots", ["Retrieval-Augmented Generation"])
    assert result.status is SupportStatus.UNSUPPORTED
    support, _ = _classify_against_profile("chatbots", ["Retrieval-Augmented Generation"])
    assert support == "unsupported"


def test_h_openai_apis_do_not_imply_production_chatbot() -> None:
    result = classify_requirement("chatbots", ["OpenAI APIs"])
    assert result.status is SupportStatus.UNSUPPORTED
    support, _ = _classify_against_profile(
        "production chatbot deployment",
        ["OpenAI APIs", "LLM application development"],
    )
    assert support == "unsupported"


def test_i_unknown_exact_normalised_match_is_direct() -> None:
    result = classify_requirement("TypeScript", ["TypeScript"])
    assert result.status is SupportStatus.SUPPORTED_DIRECT
    assert result.requested_identity is None
    support, matched = _classify_against_profile("TypeScript", ["TypeScript"])
    assert support == "supported"
    assert matched == "TypeScript"


def test_j_unknown_non_match_is_unsupported() -> None:
    result = classify_requirement("TypeScript", ["Python"])
    assert result.status is SupportStatus.UNSUPPORTED
    support, _ = _classify_against_profile("TypeScript", ["Python"])
    assert support == "unsupported"


def test_k_unknown_labels_do_not_invent_related() -> None:
    result = classify_requirement("TypeScript", ["JavaScript"])
    assert result.status is SupportStatus.UNSUPPORTED
    assert result.requested_identity is None
    support, _ = _classify_against_profile("TypeScript", ["JavaScript"])
    assert support == "unsupported"


def test_l_azure_promotes_azure_data_factory() -> None:
    support, matched = _classify_against_profile(
        "Azure",
        ["Azure Data Factory", "Python"],
    )
    assert support == "related"
    assert matched == "Azure Data Factory"
    profile = specialist_profile()
    technical = list(profile.skills.technical) + [
        Skill(name="Azure Data Factory", evidence="experience:nbn-de")
    ]
    profile = profile.model_copy(
        update={"skills": profile.skills.model_copy(update={"technical": technical})}
    )
    plan = _plan_for(analysis_with(technologies=[tech("Azure")]), profile)
    azure = _priority(plan, "Azure")
    assert azure.candidate_support == "related"
    assert azure.related_profile_capability == "Azure Data Factory"
    assert azure.may_claim_requested is False
    promoted = {name.casefold() for name in _promoted_names(plan)}
    assert "azure data factory" in promoted
    assert "azure" not in promoted


def test_m_microsoft_fabric_and_pipeline_semantics_preserved() -> None:
    fabric = classify_requirement("Microsoft Fabric", ["Azure Data Factory"])
    assert fabric.status is SupportStatus.SUPPORTED_RELATED
    assert fabric.promotable_identity == "azure_data_factory"
    assert fabric.may_claim_requested is False
    pipeline = classify_requirement("data pipeline", ["Azure Data Factory"])
    assert pipeline.status is SupportStatus.SUPPORTED_RELATED
    assert pipeline.promotable_identity == "azure_data_factory"
    azure_fabric = classify_requirement("Azure", ["Microsoft Fabric"])
    assert azure_fabric.status is SupportStatus.SUPPORTED_RELATED
    assert azure_fabric.promotable_identity == "microsoft_fabric"


def test_n_positioning_plan_and_tailoring_plan_agree_on_shared_technologies() -> None:
    profile = specialist_profile()
    job = specialist_job()
    positioning = build_positioning_plan(job, profile)
    tailoring = _plan_for(job, profile)
    tailoring_by_label = {
        item.label.casefold(): item
        for item in tailoring.jd_priorities
        if item.kind == "technology"
    }
    for need in positioning.employer_needs:
        if need.need.kind != "technology":
            continue
        priority = tailoring_by_label[need.need.label.casefold()]
        assert _PLANNER_STATUS[priority.candidate_support] is need.classification.status
        if need.classification.status is SupportStatus.SUPPORTED_RELATED:
            assert priority.related_profile_capability == (
                need.classification.promotable_profile_label
            )
            assert priority.may_claim_requested is False


def test_o_llm_is_direct_from_profile_skill_not_rag_shortcut() -> None:
    rag_only = classify_requirement("LLM", ["Retrieval-Augmented Generation"])
    assert rag_only.status is SupportStatus.UNSUPPORTED
    with_llm_skill = classify_requirement(
        "LLM",
        ["LLM application development", "Retrieval-Augmented Generation"],
    )
    assert with_llm_skill.status is SupportStatus.SUPPORTED_DIRECT
    assert with_llm_skill.promotable_profile_label == "LLM application development"


def test_p_csk_shaped_synthetic_rag_direct_bedrock_related_chatbot_gap() -> None:
    plan = _plan_for(specialist_job(), specialist_profile())
    assert _priority(plan, "RAG").candidate_support == "supported"
    bedrock = _priority(plan, "AWS Bedrock")
    assert bedrock.candidate_support == "related"
    assert bedrock.related_profile_capability == "AWS"
    assert bedrock.may_claim_requested is False
    assert _priority(plan, "chatbots").candidate_support == "unsupported"
    promoted = {name.casefold() for name in _promoted_names(plan)}
    assert "retrieval-augmented generation" in promoted
    assert "aws" in promoted
    assert "aws bedrock" not in promoted
    assert "chatbots" not in promoted


def test_q_related_requested_technology_is_never_a_promoted_skill() -> None:
    plan = _plan_for(specialist_job(), specialist_profile())
    related_labels = [
        item.label
        for item in plan.jd_priorities
        if item.kind == "technology" and item.candidate_support == "related"
    ]
    promoted = {name.casefold() for name in _promoted_names(plan)}
    for label in related_labels:
        assert label.casefold() not in promoted
        assert plan.jd_priorities  # provenance retained on the priority itself
        priority = _priority(plan, label)
        assert priority.may_claim_requested is False
        assert priority.related_profile_capability is not None


def test_r_same_input_yields_same_classification() -> None:
    profile = specialist_profile()
    job = specialist_job()
    first = DeterministicTailoringPlanner().plan(
        strategy_from_payload(job_analysis=job),
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    second = DeterministicTailoringPlanner().plan(
        strategy_from_payload(job_analysis=job),
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    assert first == second
    first_pos = build_positioning_plan(job, profile)
    second_pos = build_positioning_plan(job, profile)
    assert first_pos.model_dump() == second_pos.model_dump()


def test_openai_without_llm_skill_remains_related_for_llm_requirement() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="OpenAI APIs", evidence=None),
                        Skill(name="LangChain", evidence=None),
                    ]
                }
            )
        }
    )
    job = analysis_with(technologies=[tech("LLM"), tech("Ruby on Rails")])
    plan = _plan_for(job, profile)
    assert _priority(plan, "LLM").candidate_support == "related"
    assert _priority(plan, "Ruby on Rails").candidate_support == "unsupported"
    promoted = _promoted_names(plan)
    assert "OpenAI APIs" in promoted or "LangChain" in promoted
    assert "LLM" not in promoted
    assert "Ruby on Rails" not in promoted


def test_leftover_cicd_group_still_relates_unknown_identities() -> None:
    support, matched = _classify_against_profile(
        "Jenkins",
        ["CI/CD", "Python"],
    )
    assert support == "related"
    assert matched == "CI/CD"


def test_leftover_pipeline_phrase_still_relates_to_adf() -> None:
    support, matched = _classify_against_profile(
        "pipeline",
        ["Azure Data Factory"],
    )
    assert support == "related"
    assert matched == "Azure Data Factory"
    rag_llm = classify_requirement("LLM", ["Retrieval-Augmented Generation"])
    assert rag_llm.status is SupportStatus.UNSUPPORTED
    support_rag, _ = _classify_against_profile(
        "LLM",
        ["Retrieval-Augmented Generation"],
    )
    assert support_rag == "unsupported"
