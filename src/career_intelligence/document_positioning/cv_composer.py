"""Bounded LLM CV positioning composer.

The composer returns untrusted structured prose. ``cv_positioning`` validates
it against the evidence pack. Production package prepare does not call this.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from career_intelligence.document_positioning.cv_pack import CvPositioningPack
from career_intelligence.document_positioning.errors import (
    CvPositioningProviderError,
    CvPositioningValidationError,
    ErrorDetail,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

CV_POSITIONING_PROMPT_VERSION = "v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 60.0
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class ProjectRelevanceLine(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_name: NonEmptyString
    line: NonEmptyString = Field(max_length=220)


class CvPositioningExtraction(BaseModel):
    """Untrusted structured LLM/fixture output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: NonEmptyString
    project_relevance: list[ProjectRelevanceLine] = Field(default_factory=list, max_length=3)


class CvPositioningComposer(Protocol):
    def compose(self, pack: CvPositioningPack) -> CvPositioningExtraction:
        """Return untrusted summary and optional project relevance lines."""
        ...


class FixtureCvPositioningComposer:
    """Deterministic offline composer — no network, pack-faithful prose."""

    def compose(self, pack: CvPositioningPack) -> CvPositioningExtraction:
        summary = _fixture_summary(pack)
        relevance = _fixture_relevance(pack)
        return CvPositioningExtraction(summary=summary, project_relevance=relevance)


class OpenAICvPositioningComposer:
    """Production-ready bounded composer. Not wired into package prepare in M3."""

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
        self._instructions = load_cv_positioning_instructions()

    def compose(self, pack: CvPositioningPack) -> CvPositioningExtraction:
        from openai import OpenAIError

        try:
            response = self._client.responses.parse(  # type: ignore[attr-defined]
                model=self._model,
                instructions=self._instructions,
                input=format_cv_positioning_input(pack),
                text_format=CvPositioningExtraction,
                temperature=self._temperature,
            )
        except ValidationError as error:
            raise CvPositioningValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except OpenAIError as error:
            raise CvPositioningProviderError(
                f"OpenAI CV positioning composition failed: {error}"
            ) from error
        except Exception as error:
            raise CvPositioningProviderError(
                f"CV positioning provider failed: {error}"
            ) from error

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise CvPositioningProviderError(
                "OpenAI returned an empty structured CV positioning response"
            )
        if isinstance(parsed, CvPositioningExtraction):
            return parsed
        if isinstance(parsed, dict):
            return CvPositioningExtraction.model_validate(parsed)
        dump = getattr(parsed, "model_dump", None)
        if callable(dump):
            return CvPositioningExtraction.model_validate(dump())
        raise CvPositioningValidationError(
            [ErrorDetail(loc=("extraction",), msg="unexpected payload type", type="value_error")]
        )


def load_cv_positioning_instructions() -> str:
    path = _PROMPTS_DIR / f"cv_positioning_bounded_{CV_POSITIONING_PROMPT_VERSION}.md"
    if not path.is_file():
        raise FileNotFoundError(f"CV positioning prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def format_cv_positioning_input(pack: CvPositioningPack) -> str:
    payload = pack.model_dump(mode="json")
    return (
        "<CvPositioningPack>\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n"
        "</CvPositioningPack>\n\n"
        f"<PromptVersion>\n{CV_POSITIONING_PROMPT_VERSION}\n</PromptVersion>"
    )


def _fixture_summary(pack: CvPositioningPack) -> str:
    role = pack.role_family.replace("_", " ")
    company = pack.company
    direct = ", ".join(pack.claimable_direct_labels[:4]) or "AI Engineering"
    related = pack.related_profile_labels
    projects = ", ".join(item.name for item in pack.selected_projects[:2])
    if pack.trajectory_mode == "full_chapters":
        lead = (
            f"Software tester turned data engineer now building independent AI "
            f"Engineering systems, applying for {company}'s {role} vacancy."
        )
        middle = (
            "The hiring argument is the QA → data engineering → AI Engineering "
            "progression: commercial testing discipline, production data-platform "
            f"work, then independent AI delivery. Authorised capabilities include {direct}."
        )
    elif pack.trajectory_mode == "bridge":
        lead = (
            f"AI Engineer with commercial software-engineering discipline, "
            f"positioned for {company}'s {role} vacancy."
        )
        middle = (
            "Earlier testing and data work is used only as a reliability transfer, "
            f"not as the lead claim. Authorised capabilities include {direct}."
        )
    else:
        lead = (
            f"AI Engineer building evidence-bounded applications, positioned for "
            f"{company}'s {role} vacancy."
        )
        middle = (
            f"Lead evidence is current AI Engineering work. Authorised capabilities "
            f"include {direct}."
        )
    related_sentence = ""
    if related:
        related_sentence = (
            " Related platform evidence is "
            + ", ".join(related[:3])
            + "; requested adjacent vendor services are not claimed as hands-on experience."
        )
    project_sentence = (
        f" Packed project evidence includes {projects}." if projects else ""
    )
    return f"{lead} {middle}{related_sentence}{project_sentence}"


def _fixture_relevance(pack: CvPositioningPack) -> list[ProjectRelevanceLine]:
    lines: list[ProjectRelevanceLine] = []
    allowed = {
        label.casefold()
        for label in (*pack.claimable_direct_labels, *pack.related_profile_labels)
    }
    for project in pack.selected_projects:
        overlap = [
            tech
            for tech in project.technologies
            if any(
                tech.casefold() == label or label in tech.casefold()
                for label in allowed
            )
        ]
        if not overlap and "python" in {tech.casefold() for tech in project.technologies}:
            overlap = ["Python"]
        if not overlap:
            continue
        shown = ", ".join(overlap[:3])
        lines.append(
            ProjectRelevanceLine(
                project_name=project.name,
                line=(
                    f"demonstrates {shown} delivery from packed independent "
                    "portfolio evidence, not from unsupported employer tools."
                ),
            )
        )
        if len(lines) >= 2:
            break
    return lines
