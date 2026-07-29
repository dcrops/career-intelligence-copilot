"""Concrete acquisition adapters (paste + local export file)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from career_intelligence.job_analysis.models import JobPosting

from .acquisition import AcquisitionAdapter, AcquisitionError, AcquisitionResult
from .spike_nodes import PasteJobInput
from .state_helpers import utc_now
from .types import AcquisitionSourceKind


def _build_posting(
    raw: str,
    *,
    title: str | None,
    company: str | None,
    source_url: str | None,
) -> tuple[JobPosting, list[str]]:
    warnings: list[str] = []
    payload: dict[str, object] = {"raw_text": raw}
    if title:
        payload["title"] = title.strip()
    if company:
        payload["company"] = company.strip()
    if source_url:
        payload["source_url"] = source_url.strip()
    try:
        posting = JobPosting.model_validate(payload)
    except ValidationError as error:
        raise AcquisitionError(
            "Failed to build JobPosting from acquisition input",
            detail=str(error),
        ) from error
    return posting, warnings


@dataclass(frozen=True)
class PasteAcquisitionAdapter:
    """Deterministic paste / manual text acquisition."""

    job: PasteJobInput

    @property
    def source_kind(self) -> AcquisitionSourceKind:
        return "paste"

    def acquire(self) -> AcquisitionResult:
        raw = self.job.raw_text.strip()
        if not raw:
            raise AcquisitionError("Paste acquisition requires non-empty job text")

        title = self.job.title.strip() if self.job.title else None
        company = self.job.company.strip() if self.job.company else None
        source_url = self.job.source_url.strip() if self.job.source_url else None
        posting, warnings = _build_posting(
            raw, title=title, company=company, source_url=source_url
        )
        if source_url:
            warnings.append(
                "source_url recorded as provenance only; paste adapter does not fetch URLs"
            )

        return AcquisitionResult(
            source_kind="paste",
            source_identifier=None,
            source_url=posting.source_url,
            raw_content=raw,
            posting=posting,
            title=posting.title,
            company=posting.company,
            warnings=warnings,
            acquired_at=utc_now(),
        )


@dataclass(frozen=True)
class LocalFileAcquisitionAdapter:
    """Deterministic local file / exported job-description acquisition.

    Reads a UTF-8 text file from disk. Does not fetch URLs or call job boards.
    ``source_kind`` is ``export``.
    """

    path: Path
    title: str | None = None
    company: str | None = None
    source_url: str | None = None

    @property
    def source_kind(self) -> AcquisitionSourceKind:
        return "export"

    def acquire(self) -> AcquisitionResult:
        path = self.path.expanduser()
        if not path.is_file():
            raise AcquisitionError(f"Export file not found: {path}")

        try:
            raw = path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise AcquisitionError(
                f"Failed to read export file: {path}",
                detail=str(error),
            ) from error
        except UnicodeDecodeError as error:
            raise AcquisitionError(
                f"Export file is not valid UTF-8: {path}",
                detail=str(error),
            ) from error

        if not raw:
            raise AcquisitionError(f"Export file is empty: {path}")

        title = self.title.strip() if self.title else None
        company = self.company.strip() if self.company else None
        source_url = self.source_url.strip() if self.source_url else None
        posting, warnings = _build_posting(
            raw, title=title, company=company, source_url=source_url
        )
        warnings.append(f"Acquired from local export file: {path.name}")
        if source_url:
            warnings.append(
                "source_url recorded as provenance only; file adapter does not fetch URLs"
            )

        return AcquisitionResult(
            source_kind="export",
            source_identifier=str(path.resolve()),
            source_url=posting.source_url,
            raw_content=raw,
            posting=posting,
            title=posting.title,
            company=posting.company,
            warnings=warnings,
            acquired_at=utc_now(),
        )


def coerce_acquisition_adapter(
    source: AcquisitionAdapter | PasteJobInput,
) -> AcquisitionAdapter:
    """Accept either an adapter or legacy ``PasteJobInput`` for ``runner.start``."""
    if isinstance(source, PasteJobInput):
        return PasteAcquisitionAdapter(source)
    return source
