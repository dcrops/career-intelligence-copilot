"""Public API for the career-profile capability."""

from .evidence import (
    SkillEvidenceKind,
    evidence_strength_rank,
    resolve_skill_evidence_refs,
    strongest_evidence_kind,
    strongest_evidence_kind_for_capability,
)
from .errors import (
    ErrorDetail,
    ProfileError,
    ProfileNotFoundError,
    ProfileStorageError,
    ProfileValidationError,
    UnknownSectionError,
)
from .models import (
    CareerProfile,
    Certification,
    ExperienceEntry,
    Goals,
    Identity,
    Preferences,
    ProfileSummary,
    Project,
    Skill,
    SkillEvidenceRef,
    Skills,
)
from .sections import ProfileSection
from .service import CareerProfileService

__all__ = [
    "CareerProfile",
    "CareerProfileService",
    "Certification",
    "ErrorDetail",
    "ExperienceEntry",
    "Goals",
    "Identity",
    "Preferences",
    "ProfileError",
    "ProfileNotFoundError",
    "ProfileSection",
    "ProfileStorageError",
    "ProfileSummary",
    "ProfileValidationError",
    "Project",
    "Skill",
    "SkillEvidenceKind",
    "SkillEvidenceRef",
    "Skills",
    "UnknownSectionError",
    "evidence_strength_rank",
    "resolve_skill_evidence_refs",
    "strongest_evidence_kind",
    "strongest_evidence_kind_for_capability",
]
