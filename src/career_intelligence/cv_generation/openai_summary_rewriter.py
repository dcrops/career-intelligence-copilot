"""OpenAI Responses API summary rewriter for FR-006 Phase C.

Returns untrusted ``SummaryRewriteExtraction`` only. ``CvGenerationService``
validates allowlists and applies fail-soft fallback.
"""

from __future__ import annotations

from typing import Any, Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)
from pydantic import ValidationError

from .errors import CvGenerationError, CvGenerationValidationError, ErrorDetail
from .summary_prompt import format_summary_rewrite_input, load_summary_instructions
from .summary_rewriter import (
    SUMMARY_PROMPT_VERSION,
    SummaryRewriteExtraction,
    SummaryRewriteInput,
)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 60.0


class _ResponsesParseAPI(Protocol):
    def parse(self, **kwargs: Any) -> Any: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesParseAPI


class OpenAISummaryRewriter:
    """Package-private OpenAI rewriter. Not exported from the public package.

    Client construction matches ``OpenAIJobExtractor`` / ``OpenAIAssessor``:
    SDK default ``OPENAI_API_KEY``, optional override, model, and timeout.
    Windows SSL for live manual runs is prepared by the calling runner via
    ``truststore.inject_into_ssl()`` (same path as FR-002/003 manual scripts).
    """

    def __init__(
        self,
        *,
        client: _OpenAIClient | None = None,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        prompt_version: str = SUMMARY_PROMPT_VERSION,
        temperature: float = 0.0,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            kwargs: dict[str, object] = {"timeout": timeout}
            if api_key is not None:
                kwargs["api_key"] = api_key
            self._client = OpenAI(**kwargs)
        self._model = model
        self._prompt_version = prompt_version
        self._temperature = temperature
        self._instructions = load_summary_instructions(prompt_version)

    @property
    def model(self) -> str:
        return self._model

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    def rewrite(self, rewrite_input: SummaryRewriteInput) -> SummaryRewriteExtraction:
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=self._instructions,
                input=format_summary_rewrite_input(rewrite_input),
                text_format=SummaryRewriteExtraction,
                temperature=self._temperature,
            )
        except ValidationError as error:
            raise CvGenerationValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except OpenAIError as error:
            raise CvGenerationError(_format_openai_failure(error)) from error

        refusal = _find_refusal(response)
        if refusal is not None:
            raise CvGenerationError(
                f"OpenAI refused the summary rewrite request: {refusal}"
            )

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise CvGenerationError(
                "OpenAI returned an empty structured summary rewrite response"
            )

        return _coerce_extraction(parsed)


def _format_openai_failure(error: OpenAIError) -> str:
    """Classify provider failures for owner diagnostics (fail-soft still applies)."""
    # APITimeoutError subclasses APIConnectionError in the OpenAI SDK — check timeout first.
    if isinstance(error, APITimeoutError):
        kind = "TimeoutError"
    elif isinstance(error, APIConnectionError):
        kind = "ConnectionError"
    elif isinstance(error, AuthenticationError):
        kind = "AuthenticationError"
    elif isinstance(error, RateLimitError):
        kind = "RateLimitError"
    elif isinstance(error, APIStatusError):
        status = getattr(error, "status_code", None)
        kind = (
            f"APIStatusError(status={status})"
            if status is not None
            else "APIStatusError"
        )
    else:
        kind = type(error).__name__
    detail = str(error).strip() or repr(error)
    return f"OpenAI summary rewrite failed [{kind}]: {detail}"


def _coerce_extraction(parsed: object) -> SummaryRewriteExtraction:
    if isinstance(parsed, SummaryRewriteExtraction):
        return parsed
    if isinstance(parsed, dict):
        return SummaryRewriteExtraction.model_validate(parsed)
    dump = getattr(parsed, "model_dump", None)
    if callable(dump):
        return SummaryRewriteExtraction.model_validate(dump())
    raise CvGenerationError(
        "OpenAI summary rewrite returned an unexpected structured payload type"
    )


def _find_refusal(response: object) -> str | None:
    output = getattr(response, "output", None) or []
    for item in output:
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) == "refusal":
                refusal = getattr(content, "refusal", None)
                if isinstance(refusal, str) and refusal.strip():
                    return refusal.strip()
    return None
