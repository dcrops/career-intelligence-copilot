"""M0 capability catalogue v1 — semantic classification, not CSK-specific strings."""

from __future__ import annotations

from career_intelligence.document_positioning import (
    SupportStatus,
    classify_requirement,
    resolve_identity,
)

_RAG_ALIASES = (
    "RAG",
    "Retrieval-Augmented Generation",
    "retrieval augmented generation",
    "retrieval-augmented generation",
)


def test_rag_aliases_share_one_identity() -> None:
    identities = {resolve_identity(alias) for alias in _RAG_ALIASES}
    assert identities == {"rag"}


def test_rag_profile_evidence_is_direct_for_rag_requirement() -> None:
    result = classify_requirement(
        "RAG",
        ["Retrieval-Augmented Generation", "Python"],
    )
    assert result.status is SupportStatus.SUPPORTED_DIRECT
    assert result.requested_identity == "rag"
    assert result.may_claim_requested is True
    assert result.promotable_identity == "rag"
    assert result.promotable_profile_label == "Retrieval-Augmented Generation"


def test_retrieval_augmented_generation_requirement_is_direct_when_rag_evidenced() -> None:
    result = classify_requirement("Retrieval-Augmented Generation", ["RAG"])
    assert result.status is SupportStatus.SUPPORTED_DIRECT
    assert result.may_claim_requested is True


def test_aws_evidence_is_related_not_direct_for_bedrock_requirement() -> None:
    result = classify_requirement(
        "AWS Bedrock",
        ["AWS", "Python", "Retrieval-Augmented Generation"],
    )
    assert result.status is SupportStatus.SUPPORTED_RELATED
    assert result.requested_identity == "aws_bedrock"
    assert result.promotable_identity == "aws"
    assert result.promotable_profile_label == "AWS"
    assert result.may_claim_requested is False


def test_related_capability_cannot_be_rendered_as_requested_skill() -> None:
    result = classify_requirement("AWS Bedrock", ["AWS"])
    assert result.may_claim_requested is False
    assert result.promotable_profile_label != result.requested_label
    assert "bedrock" not in (result.promotable_profile_label or "").casefold()


def test_bedrock_evidence_would_be_direct_if_present() -> None:
    result = classify_requirement("AWS Bedrock", ["AWS Bedrock", "AWS"])
    assert result.status is SupportStatus.SUPPORTED_DIRECT
    assert result.may_claim_requested is True
    assert result.promotable_identity == "aws_bedrock"


def test_unsupported_chatbot_capability() -> None:
    result = classify_requirement(
        "chatbots",
        ["Python", "AWS", "Retrieval-Augmented Generation", "FastAPI"],
    )
    assert result.status is SupportStatus.UNSUPPORTED
    assert result.requested_identity == "chatbot"
    assert result.may_claim_requested is False
    assert result.promotable_identity is None


def test_azure_requirement_promotes_azure_data_factory_as_related() -> None:
    result = classify_requirement("Azure", ["Azure Data Factory", "Python"])
    assert result.status is SupportStatus.SUPPORTED_RELATED
    assert result.requested_identity == "azure"
    assert result.promotable_identity == "azure_data_factory"
    assert result.promotable_profile_label == "Azure Data Factory"
    assert result.may_claim_requested is False


def test_azure_data_factory_is_direct_when_evidenced() -> None:
    result = classify_requirement("Azure Data Factory", ["Azure Data Factory"])
    assert result.status is SupportStatus.SUPPORTED_DIRECT
    assert result.may_claim_requested is True


def test_java_does_not_imply_javascript() -> None:
    java_from_js = classify_requirement("Java", ["JavaScript"])
    js_from_java = classify_requirement("JavaScript", ["Java"])
    assert java_from_js.status is SupportStatus.UNSUPPORTED
    assert js_from_java.status is SupportStatus.UNSUPPORTED
    assert resolve_identity("Java") == "java"
    assert resolve_identity("JavaScript") == "javascript"
    assert resolve_identity("Java") != resolve_identity("JavaScript")


def test_aws_requirement_with_aws_evidence_is_direct() -> None:
    result = classify_requirement("AWS", ["AWS", "Python"])
    assert result.status is SupportStatus.SUPPORTED_DIRECT
    assert result.requested_identity == "aws"
    assert result.may_claim_requested is True


def test_bedrock_requirement_without_aws_is_unsupported() -> None:
    result = classify_requirement("AWS Bedrock", ["Python", "FastAPI"])
    assert result.status is SupportStatus.UNSUPPORTED
    assert result.may_claim_requested is False
    assert result.promotable_identity is None


def test_unknown_labels_do_not_invent_related_links() -> None:
    result = classify_requirement("TypeScript", ["JavaScript", "Java"])
    assert result.status is SupportStatus.UNSUPPORTED
    assert result.requested_identity is None
    assert result.may_claim_requested is False


def test_data_factory_alias_is_related_evidence_for_azure() -> None:
    result = classify_requirement("Azure", ["data factory"])
    assert result.status is SupportStatus.SUPPORTED_RELATED
    assert result.promotable_identity == "azure_data_factory"
    assert result.may_claim_requested is False
