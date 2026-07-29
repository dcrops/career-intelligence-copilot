"""Acquisition adapter contracts for FR-008.

Adapters produce a typed acquisition result; the workflow ``acquire`` node applies
it to ``WorkflowState``. The runner depends only on ``AcquisitionAdapter``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Protocol, runtime_checkable

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints

from career_intelligence.job_analysis.models import JobPosting

from .types import AcquisitionSourceKind

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AcquisitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AcquisitionResult(AcquisitionModel):
    """Normalised output of one acquisition adapter call.

    Carries provenance, posting content, and validation warnings. Does not
    mutate workflow state — the acquire node applies this result.
    """

    source_kind: AcquisitionSourceKind
    raw_content: NonEmptyString
    posting: JobPosting
    source_identifier: NonEmptyString | None = None
    source_url: AnyHttpUrl | None = None
    title: NonEmptyString | None = None
    company: NonEmptyString | None = None
    warnings: list[NonEmptyString] = Field(default_factory=list)
    acquired_at: datetime | None = None


class AcquisitionError(Exception):
    """Fail-closed acquisition failure (empty content, IO, schema)."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


@runtime_checkable
class AcquisitionAdapter(Protocol):
    """Minimal public acquisition interface.

    Implementations must be deterministic for the supported FR-008 paths
    (paste, local export file). Future adapters (URL, API, email, Playwright)
    plug in without changing the workflow runner.
    """

    @property
    def source_kind(self) -> AcquisitionSourceKind:
        """Declared source kind for this adapter instance."""

    def acquire(self) -> AcquisitionResult:
        """Fetch/normalise one job into an ``AcquisitionResult``.

        Raises ``AcquisitionError`` on unrecoverable input/IO failures.
        """
