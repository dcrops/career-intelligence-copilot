"""Bounded cover-letter positioning service (M4).

Pack → one composer call → claim/quality checks → paragraphs.
Fail closed. Does not call FR-014. Not invoked by ``cic package prepare``
in M4 (M6 owns that wiring).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.document_positioning.builder import build_positioning_plan
from career_intelligence.document_positioning.errors import (
    CoverLetterPositioningProviderError,
    CoverLetterPositioningValidationError,
    ErrorDetail,
)
from career_intelligence.document_positioning.letter_composer import (
    CoverLetterPositioningComposer,
    CoverLetterPositioningExtraction,
)
from career_intelligence.document_positioning.letter_pack import (
    CoverLetterPositioningPack,
    build_cover_letter_positioning_pack,
)
from career_intelligence.document_positioning.letter_validation import (
    validate_cover_letter_positioning_output,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.profile.models import CareerProfile


@dataclass(frozen=True)
class BoundedCoverLetterPositioningResult:
    paragraphs: tuple[str, ...]
    markdown: str
    pack: CoverLetterPositioningPack
    extraction: CoverLetterPositioningExtraction


class BoundedCoverLetterPositioningService:
    """Deterministic pack + bounded writer + fail-closed validation."""

    def __init__(self, composer: CoverLetterPositioningComposer) -> None:
        self._composer = composer

    def compose(
        self,
        job: JobAnalysis,
        profile: CareerProfile,
        *,
        strategy: ApplicationStrategy | None = None,
        assessment: OpportunityAssessment | None = None,
        contact: ContactDetails | None = None,
    ) -> BoundedCoverLetterPositioningResult:
        positioning = build_positioning_plan(job, profile, assessment=assessment)
        pack = build_cover_letter_positioning_pack(
            job,
            profile,
            positioning=positioning,
            strategy=strategy,
            assessment=assessment,
            contact=contact,
        )
        try:
            extraction = self._composer.compose(pack)
            if not isinstance(extraction, CoverLetterPositioningExtraction):
                extraction = CoverLetterPositioningExtraction.model_validate(
                    extraction
                )
        except CoverLetterPositioningProviderError:
            raise
        except CoverLetterPositioningValidationError:
            raise
        except ValidationError as error:
            raise CoverLetterPositioningValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except Exception as error:
            raise CoverLetterPositioningProviderError(
                f"Cover-letter positioning composer failed: {error}"
            ) from error

        errors = validate_cover_letter_positioning_output(
            list(extraction.paragraphs),
            pack,
        )
        if errors:
            raise CoverLetterPositioningValidationError(
                [
                    ErrorDetail(loc=("paragraphs",), msg=message, type="value_error")
                    for message in errors
                ]
            )
        paragraphs = tuple(extraction.paragraphs)
        return BoundedCoverLetterPositioningResult(
            paragraphs=paragraphs,
            markdown=_render_markdown(pack, paragraphs),
            pack=pack,
            extraction=extraction,
        )


def _render_markdown(
    pack: CoverLetterPositioningPack,
    paragraphs: tuple[str, ...],
) -> str:
    body = "\n\n".join(paragraphs)
    return (
        f"# Cover letter — {pack.prose_role_title} — {pack.company}\n\n"
        f"{body}\n\n"
        "---\n"
        "*M4 positioned cover letter (fixture or bounded composer). "
        "Owner review required. Not production package output.*\n"
    )
