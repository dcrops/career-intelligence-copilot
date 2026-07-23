"""Unit tests for FR-006 Phase C summary rewrite."""

from __future__ import annotations

from typing import Any

import pytest

from career_intelligence.cv_generation import (
    CvGenerationGateError,
    CvGenerationOptions,
    CvGenerationService,
)
from career_intelligence.cv_generation.fixture_summary_rewriter import (
    FixtureSummaryRewriter,
)
from career_intelligence.cv_generation.openai_summary_rewriter import (
    OpenAISummaryRewriter,
)
from career_intelligence.cv_generation.summary_input import (
    build_summary_rewrite_input,
    known_entity_catalogues,
)
from career_intelligence.cv_generation.summary_prompt import (
    SUMMARY_PROMPT_VERSION,
    format_summary_rewrite_input,
    load_summary_instructions,
    prompt_path,
)
from career_intelligence.cv_generation.summary_rewriter import SummaryRewriteExtraction
from career_intelligence.cv_generation.summary_validation import (
    validate_rewritten_summary,
    word_count,
)
from career_intelligence.profile.models import Skill
from tests.unit.cv_generation.helpers import (
    make_plan,
    minimal_profile,
    rich_job_analysis,
    strategy_from_payload,
)


class _FakeParseResponse:
    def __init__(self, parsed: object, *, refusal: str | None = None) -> None:
        self.output_parsed = parsed
        self.output = []
        if refusal is not None:
            content = type("C", (), {"type": "refusal", "refusal": refusal})()
            message = type("M", (), {"content": [content]})()
            self.output = [message]


class _FakeResponses:
    def __init__(self, response: _FakeParseResponse) -> None:
        self._response = response
        self.last_kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> _FakeParseResponse:
        self.last_kwargs = kwargs
        return self._response


class _FakeOpenAI:
    def __init__(self, response: _FakeParseResponse) -> None:
        self.responses = _FakeResponses(response)


def test_prompt_loads_from_versioned_file() -> None:
    path = prompt_path(SUMMARY_PROMPT_VERSION)
    assert path.is_file()
    assert SUMMARY_PROMPT_VERSION == "v2"
    text = load_summary_instructions()
    assert "Never invent technologies" in text
    assert "70–110" in text or "70-110" in text
    assert "Why should this employer keep reading" in text
    assert "Capabilities before project names" in text


def test_format_summary_input_excludes_raw_job_description() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    rewrite_input = build_summary_rewrite_input(profile, plan)
    rendered = format_summary_rewrite_input(rewrite_input)
    assert "<SourceSummary>" in rendered
    assert "<MandatoryThemes>" in rendered
    assert "<ProhibitedTechnologies>" in rendered
    assert "JobDescription" not in rendered
    assert strategy.job_analysis.posting.raw_text not in rendered
    assert "TensorFlow" in rendered  # prohibited unsupported preferred tech


def test_fixture_rewriter_is_deterministic() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    rewrite_input = build_summary_rewrite_input(profile, plan)
    rewriter = FixtureSummaryRewriter()
    first = rewriter.rewrite(rewrite_input)
    second = rewriter.rewrite(rewrite_input)
    assert first == second
    assert word_count(first.summary) <= 140


def test_validation_rejects_prohibited_technology() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    rewrite_input = build_summary_rewrite_input(profile, plan)
    catalogues = known_entity_catalogues(profile)
    result = validate_rewritten_summary(
        "AI Engineer with deep TensorFlow production experience.",
        rewrite_input,
        known_technologies=catalogues["known_technologies"]
        + ("TensorFlow",),
    )
    assert result.ok is False
    assert any("prohibited" in error or "outside the allowlist" in error for error in result.errors)


def test_validation_rejects_invented_years() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    rewrite_input = build_summary_rewrite_input(profile, plan)
    result = validate_rewritten_summary(
        "AI Engineer with 25 years of commercial AI delivery.",
        rewrite_input,
    )
    assert result.ok is False
    assert any("years-of-experience" in error for error in result.errors)


def test_validation_rejects_commercial_claim_not_in_source() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    rewrite_input = build_summary_rewrite_input(profile, plan)
    result = validate_rewritten_summary(
        "Built commercially deployed AI platforms for enterprise clients.",
        rewrite_input,
    )
    assert result.ok is False
    assert any("commercial claim" in error for error in result.errors)


def test_service_default_remains_profile_copy() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService(FixtureSummaryRewriter()).generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(tailoring_plan_approved=True),
    )
    assert cv.summary == profile.identity.summary
    assert cv.summary_source == "profile_copy"


def test_rewrite_summary_without_rewriter_raises() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    with pytest.raises(CvGenerationGateError, match="SummaryRewriter"):
        CvGenerationService().generate(
            strategy,
            profile,
            plan,
            options=CvGenerationOptions(
                tailoring_plan_approved=True,
                rewrite_summary=True,
            ),
        )


def test_fixture_rewrite_path_updates_summary_source() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="FastAPI", evidence=None),
                        Skill(name="Docker", evidence=None),
                    ]
                }
            )
        }
    )
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService(FixtureSummaryRewriter()).generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            rewrite_summary=True,
        ),
    )
    assert cv.summary_source == "fixture_rewrite"
    assert cv.summary != profile.identity.summary
    assert "Python" in (cv.summary or "")
    assert "Summary themes (from Tailoring Plan)" in cv.rendered_markdown
    assert "Phase C" in cv.rendered_markdown


def test_openai_fake_client_happy_path() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    rewrite_input = build_summary_rewrite_input(profile, plan)
    safe_summary = (
        "Test Candidate targets AI Engineer roles with evidence-backed systems. "
        "This tailored summary emphasises Python. Relevant capabilities include Python."
    )
    fake = _FakeOpenAI(
        _FakeParseResponse(SummaryRewriteExtraction(summary=safe_summary))
    )
    rewriter = OpenAISummaryRewriter(client=fake)
    extracted = rewriter.rewrite(rewrite_input)
    assert extracted.summary == safe_summary
    assert fake.responses.last_kwargs["model"] == "gpt-4o-mini"
    assert fake.responses.last_kwargs["temperature"] == 0.0
    assert "Never invent" in fake.responses.last_kwargs["instructions"]


def test_openai_failure_falls_back_to_profile_summary() -> None:
    class _BoomRewriter:
        def rewrite(self, rewrite_input):  # noqa: ANN001
            raise RuntimeError("network down")

    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService(_BoomRewriter()).generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            rewrite_summary=True,
        ),
    )
    assert cv.summary == profile.identity.summary
    assert cv.summary_source == "fallback_profile_copy"
    assert any("fell back" in item.casefold() for item in cv.assumptions)


@pytest.mark.parametrize(
    ("factory", "label"),
    [
        (
            lambda: __import__("openai").APIConnectionError(
                message="Connection error.",
                request=__import__("httpx").Request("GET", "https://api.openai.com"),
            ),
            "ConnectionError",
        ),
        (
            lambda: __import__("openai").AuthenticationError(
                message="invalid key",
                response=__import__("httpx").Response(
                    401, request=__import__("httpx").Request("GET", "https://api.openai.com")
                ),
                body=None,
            ),
            "AuthenticationError",
        ),
        (
            lambda: __import__("openai").RateLimitError(
                message="rate limited",
                response=__import__("httpx").Response(
                    429, request=__import__("httpx").Request("GET", "https://api.openai.com")
                ),
                body=None,
            ),
            "RateLimitError",
        ),
        (
            lambda: __import__("openai").APITimeoutError(
                request=__import__("httpx").Request("GET", "https://api.openai.com")
            ),
            "TimeoutError",
        ),
        (
            lambda: __import__("openai").APIStatusError(
                message="boom",
                response=__import__("httpx").Response(
                    500, request=__import__("httpx").Request("GET", "https://api.openai.com")
                ),
                body=None,
            ),
            "APIStatusError",
        ),
    ],
)
def test_openai_error_classification_labels(factory, label: str) -> None:
    from career_intelligence.cv_generation.openai_summary_rewriter import (
        _format_openai_failure,
    )

    formatted = _format_openai_failure(factory())
    assert label in formatted
    assert "OpenAI summary rewrite failed" in formatted


def test_openai_connection_error_falls_soft_with_classified_message() -> None:
    import httpx
    from openai import APIConnectionError

    class _ConnFail:
        def rewrite(self, rewrite_input):  # noqa: ANN001
            from career_intelligence.cv_generation.errors import CvGenerationError
            from career_intelligence.cv_generation.openai_summary_rewriter import (
                _format_openai_failure,
            )

            raise CvGenerationError(
                _format_openai_failure(
                    APIConnectionError(
                        message="Connection error.",
                        request=httpx.Request("GET", "https://api.openai.com"),
                    )
                )
            )

    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService(_ConnFail()).generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            rewrite_summary=True,
        ),
    )
    assert cv.summary_source == "fallback_profile_copy"
    assert any("ConnectionError" in item for item in cv.assumptions)


def test_validation_failure_falls_back() -> None:
    class _BadRewriter:
        def rewrite(self, rewrite_input):  # noqa: ANN001
            return SummaryRewriteExtraction(
                summary="Expert in TensorFlow and commercially deployed client delivery."
            )

    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService(_BadRewriter()).generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            rewrite_summary=True,
        ),
    )
    assert cv.summary_source == "fallback_profile_copy"
    assert cv.summary == profile.identity.summary


def test_openai_rewriter_not_in_public_exports() -> None:
    import career_intelligence.cv_generation as package

    assert "OpenAISummaryRewriter" not in package.__all__
    assert "FixtureSummaryRewriter" not in package.__all__
