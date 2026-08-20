"""Strong evidence-constrained LLM baseline. Independent positioning; same facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from career_intelligence.document_positioning.benchmark.evidence import (
    FactualEvidenceBundle,
    baseline_payload,
)
from career_intelligence.document_positioning.benchmark.protocol import (
    BASELINE_MODEL,
    BASELINE_PROMPT_VERSION,
    BASELINE_TEMPERATURE,
    MAX_PROVIDER_RETRIES,
    PROVIDER_TIMEOUT_SECONDS,
)
from career_intelligence.document_positioning.benchmark.retries import run_with_provider_retries

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class BaselineProviderError(RuntimeError):
    pass


class BaselineValidationError(RuntimeError):
    pass


class BaselineDocuments(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    cv_markdown: NonEmptyString
    letter_paragraphs: list[NonEmptyString] = Field(min_length=3, max_length=5)


class BaselineGenerationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    cv_markdown: str
    letter_markdown: str
    letter_paragraphs: tuple[str, ...]
    model: str
    temperature: float
    prompt_version: str
    retries_used: int
    prompt_path: str
    input_payload: dict


def load_baseline_instructions() -> str:
    path = _PROMPTS_DIR / f"baseline_positioning_{BASELINE_PROMPT_VERSION}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Baseline prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def format_baseline_input(bundle: FactualEvidenceBundle) -> str:
    payload = baseline_payload(bundle)
    return (
        "<FactualEvidenceBundle>\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n"
        "</FactualEvidenceBundle>\n\n"
        f"<PromptVersion>\n{BASELINE_PROMPT_VERSION}\n</PromptVersion>"
    )


def render_baseline_letter(
    *,
    company: str,
    role_title: str,
    paragraphs: list[str],
) -> str:
    body = "\n\n".join(paragraphs)
    return f"# Cover letter — {role_title} — {company}\n\n{body}\n"


class OpenAIBaselineComposer:
    def __init__(
        self,
        *,
        client: object | None = None,
        model: str = BASELINE_MODEL,
        api_key: str | None = None,
        timeout: float = PROVIDER_TIMEOUT_SECONDS,
        temperature: float = BASELINE_TEMPERATURE,
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
        self._instructions = load_baseline_instructions()

    def compose(self, bundle: FactualEvidenceBundle) -> BaselineDocuments:
        from openai import OpenAIError

        try:
            response = self._client.responses.parse(  # type: ignore[attr-defined]
                model=self._model,
                instructions=self._instructions,
                input=format_baseline_input(bundle),
                text_format=BaselineDocuments,
                temperature=self._temperature,
            )
        except ValidationError as error:
            raise BaselineValidationError(str(error)) from error
        except OpenAIError as error:
            raise BaselineProviderError(
                f"OpenAI baseline composition failed: {error}"
            ) from error
        except Exception as error:
            raise BaselineProviderError(f"Baseline provider failed: {error}") from error

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise BaselineProviderError("OpenAI returned an empty baseline response")
        if isinstance(parsed, BaselineDocuments):
            return parsed
        if isinstance(parsed, dict):
            return BaselineDocuments.model_validate(parsed)
        dump = getattr(parsed, "model_dump", None)
        if callable(dump):
            return BaselineDocuments.model_validate(dump())
        raise BaselineValidationError("unexpected baseline payload type")


class FixtureBaselineComposer:
    """Offline pack-faithful baseline. Not the M5 quality candidate."""

    def compose(self, bundle: FactualEvidenceBundle) -> BaselineDocuments:
        direct = ", ".join(bundle.truth.claimable_direct_labels[:4]) or "AI Engineering"
        related = ", ".join(bundle.truth.related_profile_labels[:3])
        gaps = ", ".join(bundle.truth.unsupported_labels[:4])
        related_clause = (
            f" Related platform evidence is {related}; requested adjacent vendor "
            "services are not claimed."
            if related
            else ""
        )
        gap_clause = (
            f" Honest gaps include {gaps}." if gaps else ""
        )
        cv = (
            f"# {bundle.candidate_profile['identity']['full_name']}\n\n"
            f"{bundle.master_contact_header or ''}\n\n"
            f"**{bundle.role_title}**\n\n"
            "## Professional Summary\n\n"
            f"Independent AI Engineer applying for {bundle.company}'s "
            f"{bundle.role_title} role. Authorised capabilities include {direct}."
            f"{related_clause}{gap_clause}\n\n"
            "## Selected Engineering Highlights\n\n"
            + "\n".join(f"- {item}" for item in bundle.master_highlights[:4])
            + "\n\n## Professional Experience\n\n"
            + (bundle.master_experience or "")
            + "\n"
        )
        paragraphs = [
            (
                f"{bundle.company}'s {bundle.role_title} role is relevant because "
                f"the candidate evidence includes {direct}."
            ),
            (
                "Portfolio and employment evidence in the factual bundle is used "
                "without inventing employer-requested tools."
            ),
            (
                "This letter does not claim unsupported capabilities and does not "
                "treat employer requirements as candidate experience."
            ),
        ]
        return BaselineDocuments(cv_markdown=cv, letter_paragraphs=paragraphs)


def generate_baseline_documents(
    bundle: FactualEvidenceBundle,
    composer: OpenAIBaselineComposer | FixtureBaselineComposer,
    *,
    max_retries: int = MAX_PROVIDER_RETRIES,
) -> tuple[BaselineGenerationRecord, BaselineDocuments]:
    result, retries = run_with_provider_retries(
        lambda: composer.compose(bundle),
        retryable=(BaselineProviderError, BaselineValidationError),
        max_retries=max_retries,
        label=f"{bundle.job_id} baseline",
    )
    letter = render_baseline_letter(
        company=bundle.company,
        role_title=bundle.role_title,
        paragraphs=list(result.letter_paragraphs),
    )
    model = getattr(composer, "_model", "fixture")
    temperature = getattr(composer, "_temperature", 0.0)
    record = BaselineGenerationRecord(
        job_id=bundle.job_id,
        cv_markdown=result.cv_markdown,
        letter_markdown=letter,
        letter_paragraphs=tuple(result.letter_paragraphs),
        model=str(model),
        temperature=float(temperature),
        prompt_version=BASELINE_PROMPT_VERSION,
        retries_used=retries,
        prompt_path=str(_PROMPTS_DIR / f"baseline_positioning_{BASELINE_PROMPT_VERSION}.md"),
        input_payload=baseline_payload(bundle),
    )
    return record, result
