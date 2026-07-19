"""Named sections exposed by the career-profile service."""

from enum import StrEnum


class ProfileSection(StrEnum):
    IDENTITY = "identity"
    EXPERIENCE = "experience"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    GOALS = "goals"
    PREFERENCES = "preferences"
