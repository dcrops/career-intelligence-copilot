"""CIC M3/M4 generation for the M5 harness. Does not call ``cic package prepare``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from career_intelligence.cv_generation import (
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
)
from career_intelligence.cv_generation.master_adapt import load_master_cv_markdown
from career_intelligence.document_positioning.benchmark.jobs import (
    MASTER_CV_PATH,
    FrozenEvalJob,
    eval_strategy,
    load_job_analysis,
)
from career_intelligence.document_positioning.benchmark.protocol import (
    CIC_CV_MODEL,
    CIC_LETTER_MODEL,
    CIC_TEMPERATURE,
    MAX_PROVIDER_RETRIES,
    PROVIDER_TIMEOUT_SECONDS,
)
from career_intelligence.document_positioning.benchmark.retries import run_with_provider_retries
from career_intelligence.document_positioning.cv_composer import (
    CvPositioningComposer,
    OpenAICvPositioningComposer,
)
from career_intelligence.document_positioning.cv_positioning import (
    BoundedCvPositioningResult,
    BoundedCvPositioningService,
)
from career_intelligence.document_positioning.errors import (
    CoverLetterPositioningProviderError,
    CoverLetterPositioningValidationError,
    CvPositioningProviderError,
    CvPositioningValidationError,
)
from career_intelligence.document_positioning.letter_composer import (
    CoverLetterPositioningComposer,
    OpenAICoverLetterPositioningComposer,
)
from career_intelligence.document_positioning.letter_positioning import (
    BoundedCoverLetterPositioningResult,
    BoundedCoverLetterPositioningService,
)
from career_intelligence.profile.models import CareerProfile

_CV_RETRYABLE = (CvPositioningProviderError, CvPositioningValidationError)
_LETTER_RETRYABLE = (
    CoverLetterPositioningProviderError,
    CoverLetterPositioningValidationError,
)


class CicGenerationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    cv_markdown: str
    letter_markdown: str
    letter_paragraphs: tuple[str, ...]
    cv_model: str
    letter_model: str
    temperature: float
    cv_retries_used: int
    letter_retries_used: int
    include_methodology: bool
    trajectory_mode: str
    selected_highlights: tuple[str, ...]
    selected_project_ids: tuple[str, ...]
    selected_letter_sources: tuple[str, ...]
    local_cv_validation: str
    local_letter_validation: str
    cv_pack: dict
    letter_pack: dict


class CicComposers:
    def __init__(
        self,
        cv: CvPositioningComposer,
        letter: CoverLetterPositioningComposer,
        *,
        cv_model: str,
        letter_model: str,
        temperature: float,
    ) -> None:
        self.cv = cv
        self.letter = letter
        self.cv_model = cv_model
        self.letter_model = letter_model
        self.temperature = temperature


def live_cic_composers() -> CicComposers:
    return CicComposers(
        OpenAICvPositioningComposer(
            model=CIC_CV_MODEL,
            temperature=CIC_TEMPERATURE,
            timeout=PROVIDER_TIMEOUT_SECONDS,
        ),
        OpenAICoverLetterPositioningComposer(
            model=CIC_LETTER_MODEL,
            temperature=CIC_TEMPERATURE,
            timeout=PROVIDER_TIMEOUT_SECONDS,
        ),
        cv_model=CIC_CV_MODEL,
        letter_model=CIC_LETTER_MODEL,
        temperature=CIC_TEMPERATURE,
    )


def generate_cic_documents(
    job: FrozenEvalJob,
    profile: CareerProfile,
    composers: CicComposers,
    *,
    max_retries: int = MAX_PROVIDER_RETRIES,
) -> tuple[CicGenerationRecord, BoundedCvPositioningResult, BoundedCoverLetterPositioningResult]:
    analysis = load_job_analysis(job)
    master = load_master_cv_markdown(MASTER_CV_PATH)
    tailoring = TailoringPlanService(DeterministicTailoringPlanner()).plan(
        eval_strategy(analysis, profile, job.analysis_path),
        profile,
        options=TailoringOptions(owner_approved_to_tailor=True),
    )
    cv_service = BoundedCvPositioningService(composers.cv)
    letter_service = BoundedCoverLetterPositioningService(composers.letter)

    def _cv() -> BoundedCvPositioningResult:
        return cv_service.compose(analysis, profile, tailoring, master)

    def _letter() -> BoundedCoverLetterPositioningResult:
        return letter_service.compose(
            analysis,
            profile,
            strategy=eval_strategy(analysis, profile, job.analysis_path),
        )

    cv_result, cv_retries = run_with_provider_retries(
        _cv,
        retryable=_CV_RETRYABLE,
        max_retries=max_retries,
        label=f"{job.job_id} CIC CV",
    )
    letter_result, letter_retries = run_with_provider_retries(
        _letter,
        retryable=_LETTER_RETRYABLE,
        max_retries=max_retries,
        label=f"{job.job_id} CIC cover letter",
    )
    record = CicGenerationRecord(
        job_id=job.job_id,
        cv_markdown=cv_result.markdown,
        letter_markdown=letter_result.markdown,
        letter_paragraphs=letter_result.paragraphs,
        cv_model=composers.cv_model,
        letter_model=composers.letter_model,
        temperature=composers.temperature,
        cv_retries_used=cv_retries,
        letter_retries_used=letter_retries,
        include_methodology=cv_result.pack.include_methodology,
        trajectory_mode=cv_result.pack.trajectory_mode,
        selected_highlights=cv_result.pack.selected_highlights,
        selected_project_ids=tuple(
            item.project_id for item in cv_result.pack.selected_projects
        ),
        selected_letter_sources=tuple(
            item.source_id for item in letter_result.pack.selected_sources
        ),
        local_cv_validation="pass",
        local_letter_validation="pass",
        cv_pack=cv_result.pack.model_dump(mode="json"),
        letter_pack=letter_result.pack.model_dump(mode="json"),
    )
    return record, cv_result, letter_result
