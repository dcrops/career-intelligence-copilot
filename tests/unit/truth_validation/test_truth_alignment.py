"""FR-014 truth-alignment: canonical identity, negation, duration lists, headers."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import (
    OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY,
    TruthValidationService,
    build_catalogue_from_profile,
    catalogue_supports_technology,
)
from career_intelligence.truth_validation.canonical_identity import (
    canonical_identity,
    identity_match_keys,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
LIVE_PROFILE = Path(__file__).resolve().parents[3] / "data" / "career_profile.yaml"


def _base() -> dict:
    profile = CareerProfileService.from_path(FIXTURES / "minimal_valid_profile.yaml")
    return profile.load().model_dump(mode="python")


def _profile_with_alignment_skills() -> CareerProfile:
    data = _base()
    data["skills"]["technical"].extend(
        [
            {"name": "AWS", "evidence": "experience:example-role"},
            {"name": "Java", "evidence": "experience:example-role"},
        ]
    )
    data["skills"]["domain"] = [
        {"name": "LLM application development", "evidence": "project:example-project"},
        {"name": "Retrieval-Augmented Generation", "evidence": "project:example-project"},
    ]
    return CareerProfile.model_validate(data)


def _report(markdown: str, profile: CareerProfile | None = None, extra: list[str] | None = None):
    return TruthValidationService().validate_markdown(
        markdown=markdown,
        profile=profile or _profile_with_alignment_skills(),
        context_technology_labels=extra,
    )


def _class_a(report, *keys: str):
    wanted = set(keys)
    return [
        item
        for item in report.findings
        if item.claim.claim_class == "A" and item.claim.object_key in wanted
    ]


def test_canonical_identity_llm_family_is_shared() -> None:
    assert canonical_identity("LLM") == "llm"
    assert canonical_identity("LLMs") == "llm"
    assert canonical_identity("LLM application development") == "llm"
    assert canonical_identity("large language models") is None
    keys = identity_match_keys("LLM application development")
    assert "llm" in keys
    assert "llms" in keys
    assert "llmapplicationdevelopment" in keys


def test_canonical_identity_does_not_merge_related_or_java() -> None:
    assert canonical_identity("AWS") == "aws"
    assert canonical_identity("AWS Bedrock") == "aws_bedrock"
    assert not (identity_match_keys("AWS") & identity_match_keys("AWS Bedrock"))
    assert canonical_identity("Java") == "java"
    assert canonical_identity("JavaScript") == "javascript"
    assert not (identity_match_keys("Java") & identity_match_keys("JavaScript"))


def test_llm_application_development_supports_llm_and_llms() -> None:
    profile = _profile_with_alignment_skills()
    catalogue = build_catalogue_from_profile(profile)
    assert catalogue_supports_technology(catalogue, "LLM") is not None
    assert catalogue_supports_technology(catalogue, "LLMs") is not None
    assert catalogue_supports_technology(catalogue, "LLM application development") is not None

    llm = _report("I have a foundation in LLM application development.")
    assert llm.outcome in {"pass", "warning"}
    assert any(
        item.evidence_status == "supported"
        for item in llm.findings
        if item.claim.claim_class == "A"
        and item.claim.object_key in {"llm", "llmapplicationdevelopment"}
    )

    short = _report("I have a foundation in LLM and REST APIs.", extra=["LLM"])
    assert short.outcome in {"pass", "warning"}
    blocking_llm = [
        item
        for item in short.findings
        if item.claim.claim_class == "A"
        and item.severity == "blocking"
        and "llm" in item.claim.object_key
    ]
    assert blocking_llm == []

    plural = _report("My skills include Python and LLMs.")
    assert plural.outcome in {"pass", "warning"}
    assert any(
        item.evidence_status == "supported" and item.claim.claim_class == "A"
        for item in plural.findings
        if item.claim.object_key in {"llm", "llms", "llmapplicationdevelopment"}
    )


def test_rag_abbreviation_matches_retrieval_augmented_generation() -> None:
    profile = _profile_with_alignment_skills()
    catalogue = build_catalogue_from_profile(profile)
    assert catalogue_supports_technology(catalogue, "RAG") is not None
    assert catalogue_supports_technology(catalogue, "Retrieval-Augmented Generation") is not None

    full = _report("I have experience with Retrieval-Augmented Generation.")
    assert full.outcome in {"pass", "warning"}
    abbrev = _report("I have direct skills in Python and RAG.", extra=["RAG"])
    assert abbrev.outcome in {"pass", "warning"}
    assert not any(
        item.severity == "blocking" and item.claim.object_key == "rag"
        for item in abbrev.findings
    )


def test_java_does_not_authorise_javascript() -> None:
    report = _report("I am proficient in JavaScript.", extra=["JavaScript"])
    assert report.outcome == "fail"
    assert any(
        item.claim.object_key in {"javascript", "js"} and item.severity == "blocking"
        for item in report.findings
    )


def test_aws_does_not_authorise_bedrock_experience() -> None:
    report = _report("I have direct experience with AWS Bedrock.")
    assert report.outcome == "fail"
    assert any(
        item.claim.object_key in {"awsbedrock", "bedrock"} and item.severity == "blocking"
        for item in report.findings
    )
    extensive = _report("I have worked extensively with AWS Bedrock.")
    assert extensive.outcome == "fail"


def test_bedrock_denial_is_not_a_positive_claim() -> None:
    profile = _profile_with_alignment_skills()
    denied = _report(
        "I do not have direct experience with AWS Bedrock.",
        profile,
    )
    assert not _class_a(denied, "awsbedrock", "bedrock")
    assert denied.outcome in {"pass", "warning"}

    claim_denied = _report(
        "While I do not claim direct experience with AWS Bedrock, "
        "my solid understanding of AWS technologies positions me well.",
        profile,
    )
    assert not _class_a(claim_denied, "awsbedrock", "bedrock")
    assert claim_denied.outcome in {"pass", "warning"}

    although = _report(
        "Although I have not used AWS Bedrock directly, I have AWS experience.",
        profile,
    )
    assert not _class_a(although, "awsbedrock", "bedrock")
    assert although.outcome in {"pass", "warning"}


def test_mixed_bedrock_negation_then_positive_claim_still_blocks() -> None:
    report = _report(
        "I do not claim direct Bedrock experience, but I have delivered "
        "production systems using Bedrock."
    )
    assert report.outcome == "fail"
    assert any(
        item.claim.object_key in {"awsbedrock", "bedrock"}
        and item.severity == "blocking"
        and item.claim.claim_class == "A"
        for item in report.findings
    )


def test_employer_requirement_is_not_candidate_evidence() -> None:
    report = _report(
        "The role requires AWS Bedrock experience.",
        extra=["AWS Bedrock"],
    )
    assert report.outcome in {"pass", "warning"}
    assert all(item.claim.claim_class == "B" for item in report.findings)


def test_target_role_header_is_not_a_candidate_claim() -> None:
    header = (
        "**Senior AI Engineer - AWS Bedrock | Agentic AI | "
        "Chatbots & Customer Support Auto**"
    )
    report = _report(header, extra=["AWS Bedrock", "Chatbots"])
    assert report.outcome in {"pass", "warning"}
    assert not any(item.claim.claim_class == "A" for item in report.findings)

    claimed = _report(
        header + "\n\nI have AWS Bedrock experience in production.",
        extra=["AWS Bedrock"],
    )
    assert claimed.outcome == "fail"
    assert any(
        item.claim.object_key in {"awsbedrock", "bedrock"} and item.severity == "blocking"
        for item in claimed.findings
    )


def test_in_testing_multi_domain_duration_is_overall_not_intesting() -> None:
    profile = CareerProfileService.from_path(LIVE_PROFILE).load()
    markdown = (
        "Experienced engineer with over 10 years in testing, automation, "
        "data engineering, and applied AI engineering."
    )
    report = TruthValidationService().validate_markdown(markdown=markdown, profile=profile)
    duration = [
        item
        for item in report.findings
        if item.claim.claim_kind == "duration"
    ]
    assert duration
    assert all(item.claim.object_key != "intesting" for item in duration)
    overall = next(
        item
        for item in duration
        if item.claim.object_key == OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY
    )
    assert overall.evidence_status == "supported"
    assert overall.severity == "info"
    assert report.outcome in {"pass", "warning"}


def test_across_multi_domain_duration_still_supported() -> None:
    profile = CareerProfileService.from_path(LIVE_PROFILE).load()
    markdown = (
        "Experienced engineer with 10+ years across testing, automation, "
        "data engineering and applied AI engineering."
    )
    report = TruthValidationService().validate_markdown(markdown=markdown, profile=profile)
    overall = next(
        item
        for item in report.findings
        if item.claim.claim_kind == "duration"
        and item.claim.object_key == OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY
    )
    assert overall.evidence_status == "supported"


def test_ai_only_duration_inflation_still_blocks() -> None:
    profile = CareerProfileService.from_path(LIVE_PROFILE).load()
    for markdown in (
        "I have over 10 years in AI engineering.",
        "I have 10+ years of applied AI engineering.",
        "I have 12 years of data engineering.",
    ):
        report = TruthValidationService().validate_markdown(
            markdown=markdown, profile=profile
        )
        assert report.outcome == "fail"
        assert any(
            item.claim.claim_kind == "duration" and item.severity == "blocking"
            for item in report.findings
        )
