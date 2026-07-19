"""Typed domain models for the career profile."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
]


class ProfileModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Identity(ProfileModel):
    full_name: NonEmptyString
    target_role: NonEmptyString
    summary: NonEmptyString | None = None


class ExperienceEntry(ProfileModel):
    id: Identifier
    kind: Literal["employment", "independent_engineering", "professional_development"]
    organisation: NonEmptyString
    title: NonEmptyString
    start_date: date
    end_date: date | None = None
    location: NonEmptyString | None = None
    highlights: list[NonEmptyString] = Field(default_factory=list)
    technologies: list[NonEmptyString] = Field(default_factory=list)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_month(cls, value: object) -> object:
        """Accept YYYY-MM as the first day of that month."""
        if isinstance(value, str) and len(value) == 7:
            return f"{value}-01"
        return value

    @model_validator(mode="after")
    def dates_are_ordered(self) -> ExperienceEntry:
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class Skill(ProfileModel):
    name: NonEmptyString
    evidence: NonEmptyString | None = None


class Skills(ProfileModel):
    technical: list[Skill] = Field(min_length=1)
    domain: list[Skill] = Field(default_factory=list)
    soft: list[Skill] = Field(default_factory=list)


class Project(ProfileModel):
    id: Identifier
    name: NonEmptyString
    summary: NonEmptyString
    technologies: list[NonEmptyString] = Field(default_factory=list)
    outcomes: list[NonEmptyString] = Field(default_factory=list)
    url: AnyHttpUrl | None = None
    demonstrates: list[NonEmptyString] = Field(default_factory=list)


class Certification(ProfileModel):
    id: Identifier
    name: NonEmptyString
    issuer: NonEmptyString
    status: Literal["active", "expired"]
    date_obtained: date | None = None
    expiry_date: date | None = None
    url: AnyHttpUrl | None = None

    @field_validator("date_obtained", "expiry_date", mode="before")
    @classmethod
    def parse_month(cls, value: object) -> object:
        if isinstance(value, str) and len(value) == 7:
            return f"{value}-01"
        return value


class Goals(ProfileModel):
    primary: NonEmptyString
    secondary: list[NonEmptyString] = Field(default_factory=list)
    horizon_notes: NonEmptyString | None = None


class Preferences(ProfileModel):
    locations: list[NonEmptyString] = Field(default_factory=list)
    employment_types: list[Literal["full_time", "contract", "part_time"]] = Field(
        default_factory=list
    )
    salary_min: int | None = Field(default=None, ge=0)
    salary_currency: Literal["AUD", "USD", "GBP", "EUR", "CAD", "NZD", "SGD"] | None = None
    remote: Literal["onsite", "hybrid", "remote", "flexible"]
    company_stages: list[NonEmptyString] = Field(default_factory=list)
    must_haves: list[NonEmptyString] = Field(default_factory=list)
    deal_breakers: list[NonEmptyString] = Field(default_factory=list)


class CareerProfile(ProfileModel):
    schema_version: Literal["1"]
    identity: Identity
    experience: list[ExperienceEntry] = Field(default_factory=list)
    skills: Skills
    projects: list[Project] = Field(min_length=1)
    certifications: list[Certification] = Field(default_factory=list)
    goals: Goals
    preferences: Preferences

    @model_validator(mode="after")
    def entity_ids_are_unique(self) -> CareerProfile:
        for field_name in ("experience", "projects", "certifications"):
            entries = getattr(self, field_name)
            identifiers = [entry.id for entry in entries]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{field_name} ids must be unique")
        return self


class ProfileSummary(ProfileModel):
    full_name: str
    target_role: str
    technical_skill_count: int
    domain_skill_count: int
    soft_skill_count: int
    project_count: int
    certification_count: int
    primary_goal: str
