"""Public API for CV generation (FR-006 — complete).

Phase A: TailoringPlan via TailoringPlanService + DeterministicTailoringPlanner.
Phase B: TailoredCv via CvGenerationService (deterministic Markdown render).
Phase C: Optional theme-guided summary rewrite (opt-in rewrite_summary + rewriter).

OpenAI and fixture summary rewriters are package-private — inject explicitly.
"""

from .baseline import active_certifications_baseline
from .deterministic_planner import DeterministicTailoringPlanner
from .draft_writer import (
    DraftWriteResult,
    build_draft_stem,
    default_generated_dir,
    write_tailored_cv_drafts,
)
from .errors import (
    CvGenerationError,
    CvGenerationGateError,
    CvGenerationValidationError,
    ErrorDetail,
    TailoringPlanGateError,
    TailoringPlanValidationError,
)
from .experience_scope import (
    is_extended_history_experience_id,
    temporary_extended_history_experience_ids,
)
from .generation_service import CvGenerationService
from .models import (
    DeprioritisedSkill,
    EmphasisedProject,
    ExperienceGuidance,
    JdPriority,
    PromotedSkill,
    SummaryTheme,
    TailoredCv,
    TailoringPlan,
)
from .options import ContactDetails, CvGenerationOptions, TailoringOptions
from .plan_service import TailoringPlanService
from .render_markdown import render_markdown

__all__ = [
    "ContactDetails",
    "CvGenerationError",
    "CvGenerationGateError",
    "CvGenerationOptions",
    "CvGenerationService",
    "CvGenerationValidationError",
    "DeprioritisedSkill",
    "DeterministicTailoringPlanner",
    "DraftWriteResult",
    "EmphasisedProject",
    "ErrorDetail",
    "ExperienceGuidance",
    "JdPriority",
    "PromotedSkill",
    "SummaryTheme",
    "TailoredCv",
    "TailoringOptions",
    "TailoringPlan",
    "TailoringPlanGateError",
    "TailoringPlanService",
    "TailoringPlanValidationError",
    "active_certifications_baseline",
    "build_draft_stem",
    "default_generated_dir",
    "is_extended_history_experience_id",
    "render_markdown",
    "temporary_extended_history_experience_ids",
    "write_tailored_cv_drafts",
]
