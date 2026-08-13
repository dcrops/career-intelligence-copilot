"""Bounded LLM cover-letter composer (package-private experiment).

One structured generation call. The composer returns untrusted paragraphs;
``bounded_generation`` validates them against the evidence pack.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from career_intelligence.cover_letter.errors import (
    CoverLetterError,
    CoverLetterGenerationValidationError,
    ErrorDetail,
)
from career_intelligence.cover_letter.evidence_pack import CoverLetterEvidencePack

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

COVER_LETTER_BOUNDED_PROMPT_VERSION = "v2"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 60.0

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class CoverLetterExtraction(BaseModel):
    """Untrusted structured LLM/fixture output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    paragraphs: list[NonEmptyString] = Field(min_length=3, max_length=5)


class CoverLetterComposer(Protocol):
    def compose(self, pack: CoverLetterEvidencePack) -> CoverLetterExtraction:
        """Return untrusted letter paragraphs."""
        ...


class FixtureCoverLetterComposer:
    """Deterministic offline composer — no network, pack-faithful prose."""

    def compose(self, pack: CoverLetterEvidencePack) -> CoverLetterExtraction:
        company = pack.role_context.company
        role = pack.role_context.role_title
        opening_need = (
            pack.role_context.responsibilities[0]
            if pack.role_context.responsibilities
            else "production-minded AI Engineering delivery"
        )
        opening = (
            f"{company}'s {role} role is relevant because it asks for "
            f"{_trim(opening_need, 140)}. I can contribute from the packed "
            f"engineering evidence below rather than from generic enthusiasm."
        )

        independent = next(
            (
                item
                for item in pack.experience
                if item.relationship == "independent_rd"
            ),
            None,
        )
        commercial = next(
            (
                item
                for item in pack.experience
                if item.relationship == "commercial_employment"
                and "data engineer" in item.title.casefold()
            ),
            None,
        )
        if commercial is None:
            commercial = next(
                (
                    item
                    for item in pack.experience
                    if item.relationship == "commercial_employment"
                ),
                None,
            )
        testing = next(
            (
                item
                for item in pack.experience
                if item.relationship == "commercial_employment"
                and "test" in item.title.casefold()
            ),
            None,
        )
        trajectory_parts: list[str] = []
        if testing:
            trajectory_parts.append(
                f"Earlier commercial software testing and automation at "
                f"{testing.organisation} informs how I verify and test AI "
                "systems today."
            )
        if commercial:
            trajectory_parts.append(
                f"I later worked commercially as {commercial.title} at "
                f"{commercial.organisation}, which is employment, not AI-vendor "
                "delivery."
            )
        if independent:
            trajectory_parts.append(
                f"Current AI work is independent research and development as "
                f"{independent.title} at {independent.organisation}, distinct "
                "from conventional commercial employment."
            )
        if not trajectory_parts and pack.identity_summary:
            trajectory_parts.append(_trim(pack.identity_summary, 280))
        trajectory = " ".join(trajectory_parts) or (
            f"I am targeting {pack.target_role} roles with the packed evidence."
        )

        project_sentences: list[str] = []
        for item in pack.projects:
            tech = ", ".join(item.technologies[:4])
            tech_clause = f" Relevant technical evidence includes {tech}." if tech else ""
            project_sentences.append(
                f"I developed {item.name}: {item.purpose} "
                f"{item.what_was_built}.{tech_clause}"
            )
        projects = " ".join(project_sentences) or (
            "Selected portfolio evidence is listed in the pack."
        )
        paragraphs = [opening, trajectory, projects]
        if pack.contact.portfolio_url and pack.contact.github_url:
            paragraphs.append(
                "The Portfolio and GitHub in the header are the working examples "
                "of the packed projects, including how they were built, tested, "
                "and structured."
            )
        paragraphs.append(
            f"This packed engineering evidence is directly useful to "
            f"{company}'s {role} work."
        )
        return CoverLetterExtraction(paragraphs=paragraphs)


class _ResponsesParseAPI(Protocol):
    def parse(self, **kwargs: Any) -> Any: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesParseAPI


class OpenAICoverLetterComposer:
    """Production bounded cover-letter composer (one structured OpenAI call)."""

    def __init__(
        self,
        *,
        client: _OpenAIClient | None = None,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        prompt_version: str = COVER_LETTER_BOUNDED_PROMPT_VERSION,
        temperature: float = 0.2,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI

            try:
                import truststore

                truststore.inject_into_ssl()
            except ImportError:
                pass
            kwargs: dict[str, object] = {"timeout": timeout}
            if api_key is not None:
                kwargs["api_key"] = api_key
            self._client = OpenAI(**kwargs)
        self._model = model
        self._prompt_version = prompt_version
        self._temperature = temperature
        self._instructions = load_cover_letter_instructions(prompt_version)

    @property
    def model(self) -> str:
        return self._model

    def compose(self, pack: CoverLetterEvidencePack) -> CoverLetterExtraction:
        from openai import OpenAIError

        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=self._instructions,
                input=format_cover_letter_input(pack),
                text_format=CoverLetterExtraction,
                temperature=self._temperature,
            )
        except ValidationError as error:
            raise CoverLetterGenerationValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except OpenAIError as error:
            raise CoverLetterError(
                f"OpenAI cover letter composition failed: {error}"
            ) from error

        refusal = _find_refusal(response)
        if refusal is not None:
            raise CoverLetterError(
                f"OpenAI refused the cover letter request: {refusal}"
            )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise CoverLetterError(
                "OpenAI returned an empty structured cover letter response"
            )
        return _coerce_extraction(parsed)


def load_cover_letter_instructions(
    version: str = COVER_LETTER_BOUNDED_PROMPT_VERSION,
) -> str:
    path = _PROMPTS_DIR / f"cover_letter_bounded_{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Cover letter prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def format_cover_letter_input(pack: CoverLetterEvidencePack) -> str:
    payload = pack.model_dump(mode="json")
    return (
        "<EvidencePack>\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n"
        "</EvidencePack>\n\n"
        f"<PromptVersion>\n{COVER_LETTER_BOUNDED_PROMPT_VERSION}\n</PromptVersion>"
    )


def _coerce_extraction(parsed: object) -> CoverLetterExtraction:
    if isinstance(parsed, CoverLetterExtraction):
        return parsed
    if isinstance(parsed, dict):
        return CoverLetterExtraction.model_validate(parsed)
    dump = getattr(parsed, "model_dump", None)
    if callable(dump):
        return CoverLetterExtraction.model_validate(dump())
    raise CoverLetterError(
        "OpenAI cover letter composition returned an unexpected payload type"
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


def _trim(text: str, limit: int) -> str:
    cleaned = " ".join(text.split()).rstrip(".")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0] + "…"
