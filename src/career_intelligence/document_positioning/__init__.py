"""Document positioning: catalogue, PositioningPlan, CV and cover-letter composers.

The catalogue is the shared semantic authority for TailoringPlan planning and
PositioningPlan. Bounded CV positioning (M3) and cover-letter positioning (M4)
are implemented here but are **not** invoked by ``cic package prepare``
(M6 owns that wiring). Master-adapt, production cover-letter generation, and
package prepare still must not import PositioningPlan.
"""

from .builder import build_positioning_plan
from .catalogue import (
    aliases_for_identity,
    classify_requirement,
    identities_mentioned_in_text,
    normalise_label,
    resolve_identity,
    supporting_identities,
)
from .cv_composer import (
    CvPositioningComposer,
    CvPositioningExtraction,
    FixtureCvPositioningComposer,
)
from .cv_pack import CvPositioningPack, build_cv_positioning_pack
from .cv_positioning import BoundedCvPositioningResult, BoundedCvPositioningService
from .errors import (
    CoverLetterPositioningError,
    CoverLetterPositioningProviderError,
    CoverLetterPositioningValidationError,
    CvPositioningError,
    CvPositioningProviderError,
    CvPositioningValidationError,
)
from .letter_composer import (
    CoverLetterPositioningComposer,
    CoverLetterPositioningExtraction,
    FixtureCoverLetterPositioningComposer,
)
from .letter_pack import CoverLetterPositioningPack, build_cover_letter_positioning_pack
from .letter_positioning import (
    BoundedCoverLetterPositioningResult,
    BoundedCoverLetterPositioningService,
)
from .letter_selection import (
    DEFAULT_SOURCE_COUNT,
    MAX_SOURCE_COUNT,
    EvidenceSelection,
    select_cover_letter_evidence,
)
from .models import (
    CV_REWRITE_SURFACE,
    LOCKED_MASTER_SECTIONS,
    ArgumentClaim,
    CandidateEvidenceRef,
    ClassifiedNeed,
    EmployerNeed,
    ForbiddenClaim,
    PositioningPlan,
    RequirementClassification,
    SupportStatus,
)
from .render import render_positioning_plan

__all__ = [
    "CV_REWRITE_SURFACE",
    "DEFAULT_SOURCE_COUNT",
    "LOCKED_MASTER_SECTIONS",
    "MAX_SOURCE_COUNT",
    "ArgumentClaim",
    "BoundedCoverLetterPositioningResult",
    "BoundedCoverLetterPositioningService",
    "BoundedCvPositioningResult",
    "BoundedCvPositioningService",
    "CandidateEvidenceRef",
    "ClassifiedNeed",
    "CoverLetterPositioningComposer",
    "CoverLetterPositioningError",
    "CoverLetterPositioningExtraction",
    "CoverLetterPositioningPack",
    "CoverLetterPositioningProviderError",
    "CoverLetterPositioningValidationError",
    "CvPositioningComposer",
    "CvPositioningError",
    "CvPositioningExtraction",
    "CvPositioningPack",
    "CvPositioningProviderError",
    "CvPositioningValidationError",
    "EmployerNeed",
    "EvidenceSelection",
    "FixtureCoverLetterPositioningComposer",
    "FixtureCvPositioningComposer",
    "ForbiddenClaim",
    "PositioningPlan",
    "RequirementClassification",
    "SupportStatus",
    "aliases_for_identity",
    "build_cover_letter_positioning_pack",
    "build_cv_positioning_pack",
    "build_positioning_plan",
    "classify_requirement",
    "identities_mentioned_in_text",
    "normalise_label",
    "render_positioning_plan",
    "resolve_identity",
    "select_cover_letter_evidence",
    "supporting_identities",
]
