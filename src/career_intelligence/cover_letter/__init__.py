"""Public API for cover letter generation (FR-007).

Phase A: CoverLetterPlan via CoverLetterPlanService + DeterministicCoverLetterPlanner.
Phase B: CoverLetter via CoverLetterGenerationService (deterministic Markdown + HTML).

Owner review is mandatory before any external use.
"""

from career_intelligence.cv_generation.options import ContactDetails

from .deterministic_planner import DeterministicCoverLetterPlanner
from .draft_writer import (
    DraftWriteResult,
    build_draft_stem,
    default_generated_dir,
    write_cover_letter_drafts,
)
from .errors import (
    CoverLetterError,
    CoverLetterGenerationGateError,
    CoverLetterGenerationValidationError,
    CoverLetterPdfRenderError,
    CoverLetterPlanGateError,
    CoverLetterPlanValidationError,
    ErrorDetail,
)
from .generation_service import CoverLetterGenerationService
from .html_renderer import CoverLetterHtmlRenderError, render_html
from .models import (
    ClosingStrategy,
    CompanyAlignment,
    CoverLetter,
    CoverLetterPlan,
    RelevantEvidence,
    RoleMotivation,
    StrongestProject,
)
from .options import CoverLetterGenerationOptions, CoverLetterPlanOptions
from .plan_service import CoverLetterPlanService
from .render_markdown import render_markdown

__all__ = [
    "ClosingStrategy",
    "CompanyAlignment",
    "ContactDetails",
    "CoverLetter",
    "CoverLetterError",
    "CoverLetterGenerationGateError",
    "CoverLetterGenerationOptions",
    "CoverLetterGenerationService",
    "CoverLetterGenerationValidationError",
    "CoverLetterHtmlRenderError",
    "CoverLetterPdfRenderError",
    "CoverLetterPlan",
    "CoverLetterPlanGateError",
    "CoverLetterPlanOptions",
    "CoverLetterPlanService",
    "CoverLetterPlanValidationError",
    "DeterministicCoverLetterPlanner",
    "DraftWriteResult",
    "ErrorDetail",
    "RelevantEvidence",
    "RoleMotivation",
    "StrongestProject",
    "build_draft_stem",
    "default_generated_dir",
    "render_html",
    "render_markdown",
    "write_cover_letter_drafts",
]
