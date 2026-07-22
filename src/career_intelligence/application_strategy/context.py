"""Optional search-operating context for FR-005 Application Strategy."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SearchOperatingContext(BaseModel):
    """Caller-supplied search posture for strategy planning.

    Intentionally small for v1. Volume applications are opt-in; quotas and
    JobSeeker counters are deferred until a later requirement needs them.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    volume_applications_enabled: bool = False
    notes: NonEmptyString | None = None
