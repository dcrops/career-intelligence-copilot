"""Bounded LLM cover-letter positioning composer (M4).

The composer returns untrusted paragraphs. ``letter_positioning`` validates
them against the evidence pack. Production package prepare does not call this.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from career_intelligence.document_positioning.errors import (
    CoverLetterPositioningProviderError,
    CoverLetterPositioningValidationError,
    ErrorDetail,
)
from career_intelligence.document_positioning.letter_pack import CoverLetterPositioningPack
from career_intelligence.document_positioning.models import SupportStatus

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

COVER_LETTER_POSITIONING_PROMPT_VERSION = "v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 60.0
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class CoverLetterPositioningExtraction(BaseModel):
    """Untrusted structured LLM/fixture output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    paragraphs: list[NonEmptyString] = Field(min_length=3, max_length=5)


class CoverLetterPositioningComposer(Protocol):
    def compose(
        self, pack: CoverLetterPositioningPack
    ) -> CoverLetterPositioningExtraction:
        """Return untrusted letter paragraphs."""
        ...


class FixtureCoverLetterPositioningComposer:
    """Deterministic offline composer — no network, pack-faithful prose."""

    def compose(
        self, pack: CoverLetterPositioningPack
    ) -> CoverLetterPositioningExtraction:
        paragraphs = _fixture_paragraphs(pack)
        return CoverLetterPositioningExtraction(paragraphs=paragraphs)


class OpenAICoverLetterPositioningComposer:
    """Production-ready bounded composer. Not wired into package prepare in M4."""

    def __init__(
        self,
        *,
        client: object | None = None,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
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
        self._temperature = temperature
        self._instructions = load_cover_letter_positioning_instructions()

    def compose(
        self, pack: CoverLetterPositioningPack
    ) -> CoverLetterPositioningExtraction:
        from openai import OpenAIError

        try:
            response = self._client.responses.parse(  # type: ignore[attr-defined]
                model=self._model,
                instructions=self._instructions,
                input=format_cover_letter_positioning_input(pack),
                text_format=CoverLetterPositioningExtraction,
                temperature=self._temperature,
            )
        except ValidationError as error:
            raise CoverLetterPositioningValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except OpenAIError as error:
            raise CoverLetterPositioningProviderError(
                f"OpenAI cover-letter positioning composition failed: {error}"
            ) from error
        except Exception as error:
            raise CoverLetterPositioningProviderError(
                f"Cover-letter positioning provider failed: {error}"
            ) from error

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise CoverLetterPositioningProviderError(
                "OpenAI returned an empty structured cover-letter positioning response"
            )
        if isinstance(parsed, CoverLetterPositioningExtraction):
            return parsed
        if isinstance(parsed, dict):
            return CoverLetterPositioningExtraction.model_validate(parsed)
        dump = getattr(parsed, "model_dump", None)
        if callable(dump):
            return CoverLetterPositioningExtraction.model_validate(dump())
        raise CoverLetterPositioningValidationError(
            [
                ErrorDetail(
                    loc=("extraction",),
                    msg="unexpected payload type",
                    type="value_error",
                )
            ]
        )


def load_cover_letter_positioning_instructions() -> str:
    path = (
        _PROMPTS_DIR
        / f"cover_letter_positioning_bounded_{COVER_LETTER_POSITIONING_PROMPT_VERSION}.md"
    )
    if not path.is_file():
        raise FileNotFoundError(f"Cover-letter positioning prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def format_cover_letter_positioning_input(pack: CoverLetterPositioningPack) -> str:
    payload = pack.model_dump(mode="json")
    return (
        "<CoverLetterPositioningPack>\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n"
        "</CoverLetterPositioningPack>\n\n"
        f"<PromptVersion>\n{COVER_LETTER_POSITIONING_PROMPT_VERSION}\n</PromptVersion>"
    )


def _fixture_paragraphs(pack: CoverLetterPositioningPack) -> list[str]:
    opening = _fixture_opening(pack)
    bodies = _fixture_bodies(pack)
    closing = _fixture_closing(pack)
    paragraphs = [opening, *bodies, closing]
    if len(paragraphs) < 3:
        paragraphs.insert(
            1,
            _trim(
                "Packed independent AI Engineering evidence is listed in the "
                "selected sources and is distinct from commercial AI employment.",
                280,
            ),
        )
    return paragraphs[:5]


def _fixture_opening(pack: CoverLetterPositioningPack) -> str:
    direct = ", ".join(pack.claimable_direct_labels[:3]) or "packed AI Engineering work"
    anchors = [item.name for item in pack.selected_sources[:2]]
    anchor_text = " and ".join(anchors) if anchors else "packed evidence"
    related = pack.related_profile_labels
    related_clause = ""
    if related:
        related_clause = (
            f" Related platform grounding is {', '.join(related[:2])}; "
            "requested adjacent vendor services are not claimed as hands-on experience."
        )
    role = pack.prose_role_title
    if pack.trajectory_mode == "full_chapters":
        lead = (
            f"{pack.company}'s {role} role is a fit for a tester-to-"
            f"data-engineer-to-AI-engineer path, not a generic application."
        )
    elif pack.trajectory_mode == "bridge":
        lead = (
            f"{pack.company}'s {role} role is relevant because packed "
            f"AI delivery can transfer from prior engineering discipline."
        )
    else:
        lead = (
            f"{pack.company}'s {role} role is relevant because it "
            f"asks for {direct}, which the packed evidence can support."
        )
    return (
        f"{lead} The strongest truthful anchors are {anchor_text}.{related_clause}"
    )


def _fixture_bodies(pack: CoverLetterPositioningPack) -> list[str]:
    bodies: list[str] = []
    for source in pack.selected_sources:
        if source.source_type == "trajectory":
            bodies.append(_trajectory_paragraph(pack, source.facts))
            continue
        fact = source.facts[0] if source.facts else source.purpose
        tech = ", ".join(source.technologies[:4])
        tech_clause = f" Packed technical evidence includes {tech}." if tech else ""
        covered_direct = [
            label
            for label, kind in zip(
                source.employer_needs_covered, source.coverage_kinds, strict=False
            )
            if kind == "direct"
        ]
        if "related" in source.coverage_kinds:
            cover_clause = (
                " This is RELATED transfer evidence: the packed profile "
                "capability is promoted and the requested vendor identity is not claimed."
            )
        elif covered_direct:
            cover_clause = (
                f" This answers employer need(s) {', '.join(covered_direct[:3])} "
                "without inventing unlisted tools."
            )
        else:
            cover_clause = " This is packed supporting evidence for the role."
        if source.source_type == "employment":
            sentence = (
                f"Commercial evidence from {source.name}: {fact}{tech_clause}"
                f"{cover_clause}"
            )
        elif source.source_type == "independent_engineering":
            sentence = (
                f"Independent engineering at {source.organisation or source.name} "
                f"is not commercial AI employment. {fact}{tech_clause}{cover_clause}"
            )
        elif source.source_type == "certification":
            sentence = (
                f"Certification evidence: {source.name}.{cover_clause}"
            )
        else:
            sentence = (
                f"I developed {source.name} as independent portfolio work. "
                f"{fact}{tech_clause}{cover_clause}"
            )
        bodies.append(_trim(sentence, 420))
    return bodies[:3]


def _trajectory_paragraph(pack: CoverLetterPositioningPack, facts: tuple[str, ...]) -> str:
    joined = " ".join(facts) if facts else (
        "The packed career path runs commercial testing, then data engineering, "
        "then independent AI Engineering."
    )
    extra = ""
    if pack.include_methodology:
        extra = (
            " Testing discipline and human review remain relevant to adoption "
            "and reliability work."
        )
    return _trim(joined + extra, 420)


def _fixture_closing(pack: CoverLetterPositioningPack) -> str:
    gaps = [
        item.label
        for item in pack.employer_needs
        if item.status is SupportStatus.UNSUPPORTED
    ]
    gap_clause = ""
    if gaps and pack.role_family == "ai_engineering" and any(
        token in " ".join(gaps).casefold() for token in ("gpu", "linux", "hpc")
    ):
        gap_clause = (
            " I do not claim GPU, Linux, or HPC employment; the packed case is "
            "applied AI and Python delivery only."
        )
    return (
        f"This packed evidence is useful to {pack.company}'s {pack.prose_role_title} "
        f"work because it answers the selected employer needs without overclaim."
        f"{gap_clause}"
    )


def _trim(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0] + "…"
