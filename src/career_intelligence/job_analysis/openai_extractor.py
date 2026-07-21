"""OpenAI Responses API extractor for FR-002 Job Analysis.

Returns an untrusted ``JobAnalysisPayload`` only. ``JobAnalysisService`` binds the
caller-supplied ``JobPosting`` and validates the trusted ``JobAnalysis``.
"""

from __future__ import annotations

from typing import Any, Protocol

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from .errors import ErrorDetail, JobAnalysisError, JobAnalysisValidationError
from .extraction import JobAnalysisExtraction
from .extraction_prompt import EXTRACTION_INSTRUCTIONS_V1
from .extractor import JobAnalysisPayload
from .models import JobPosting

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 60.0


class _ResponsesParseAPI(Protocol):
    def parse(self, **kwargs: Any) -> Any: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesParseAPI


class OpenAIJobExtractor:
    """Concrete ``JobExtractor`` backed by the OpenAI Responses API.

    Satisfies ``JobExtractor`` by structural typing. Configuration is intentionally
    minimal: API key (via SDK / override), model, and timeout.
    """

    def __init__(
        self,
        *,
        client: _OpenAIClient | None = None,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            kwargs: dict[str, object] = {"timeout": timeout}
            if api_key is not None:
                kwargs["api_key"] = api_key
            self._client = OpenAI(**kwargs)
        self._model = model

    def extract(self, posting: JobPosting) -> JobAnalysisPayload:
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=EXTRACTION_INSTRUCTIONS_V1,
                input=_format_posting_input(posting),
                text_format=JobAnalysisExtraction,
            )
        except ValidationError as error:
            raise JobAnalysisValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except OpenAIError as error:
            raise JobAnalysisError(f"OpenAI extraction failed: {error}") from error

        refusal = _find_refusal(response)
        if refusal is not None:
            raise JobAnalysisError(f"OpenAI refused the extraction request: {refusal}")

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise JobAnalysisError("OpenAI returned an empty structured extraction response")

        extraction = _coerce_extraction(parsed)
        return extraction.model_dump(mode="python")


def _format_posting_input(posting: JobPosting) -> str:
    """Render trusted JobPosting fields as provenance-tagged sections.

    Title, company, and source URL are first-class extraction inputs — not only the
    description body. Location is not a JobPosting field today; when present later it
    should be tagged the same way.
    """
    parts: list[str] = []
    if posting.title is not None:
        parts.append(_tagged("JobTitle", posting.title))
    if posting.company is not None:
        parts.append(_tagged("Company", posting.company))
    if posting.source_url is not None:
        parts.append(_tagged("SourceURL", str(posting.source_url)))
    parts.append(_tagged("JobDescription", posting.raw_text))
    return "\n\n".join(parts)


def _tagged(name: str, content: str) -> str:
    return f"<{name}>\n{content}\n</{name}>"


def _find_refusal(response: object) -> str | None:
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) == "refusal":
                refusal = getattr(content, "refusal", None)
                return str(refusal) if refusal else "Model refused the request"
    return None


def _coerce_extraction(parsed: object) -> JobAnalysisExtraction:
    if isinstance(parsed, JobAnalysisExtraction):
        return parsed
    try:
        return JobAnalysisExtraction.model_validate(parsed)
    except ValidationError as error:
        raise JobAnalysisValidationError(
            [ErrorDetail.from_pydantic(item) for item in error.errors()]
        ) from error
