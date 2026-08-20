"""Blind Version A / Version B mapping. Do not leak into owner artefacts."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random

from pydantic import BaseModel, ConfigDict

from career_intelligence.document_positioning.benchmark.protocol import (
    SystemId,
    VersionLabel,
)

HIDDEN_MAPPING_FILENAME = "ab_mapping.json"
HIDDEN_README = """# DO NOT OPEN BEFORE OWNER SCORING IS COMPLETE

This directory identifies which Version A / Version B is CIC versus the
strong LLM baseline.

Opening it before scoring destroys the blind comparison.

After you have filled every scoring sheet, tell the agent the scores are
complete. Only then may the mapping be revealed.
"""


class JobVersionAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str
    version_a: SystemId
    version_b: SystemId


class BlindMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    assignments: tuple[JobVersionAssignment, ...]
    revealed: bool = False

    def system_for(self, job_id: str, version: VersionLabel) -> SystemId:
        assignment = self.assignment(job_id)
        return assignment.version_a if version == "A" else assignment.version_b

    def version_for(self, job_id: str, system: SystemId) -> VersionLabel:
        assignment = self.assignment(job_id)
        if assignment.version_a == system:
            return "A"
        if assignment.version_b == system:
            return "B"
        raise KeyError(f"{system} not assigned for {job_id}")

    def assignment(self, job_id: str) -> JobVersionAssignment:
        for item in self.assignments:
            if item.job_id == job_id:
                return item
        raise KeyError(job_id)


def build_blind_mapping(
    job_ids: tuple[str, ...],
    *,
    rng: Random,
) -> BlindMapping:
    assignments: list[JobVersionAssignment] = []
    for job_id in job_ids:
        cic_is_a = bool(rng.randrange(2))
        assignments.append(
            JobVersionAssignment(
                job_id=job_id,
                version_a="cic" if cic_is_a else "baseline",
                version_b="baseline" if cic_is_a else "cic",
            )
        )
    return BlindMapping(assignments=tuple(assignments), revealed=False)


def persist_mapping(mapping: BlindMapping, hidden_dir: Path) -> Path:
    hidden_dir.mkdir(parents=True, exist_ok=True)
    (hidden_dir / "README.md").write_text(HIDDEN_README, encoding="utf-8")
    path = hidden_dir / HIDDEN_MAPPING_FILENAME
    path.write_text(
        mapping.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_mapping(path: Path) -> BlindMapping:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BlindMapping.model_validate(payload)


def reveal_mapping(mapping: BlindMapping) -> BlindMapping:
    """Return a copy marked revealed. Call only after owner scoring exists."""
    return mapping.model_copy(update={"revealed": True})


def mapping_leaks_in_text(text: str, mapping: BlindMapping) -> list[str]:
    """Return leak phrases if a mapping assignment is visible in owner text."""
    folded = text.casefold()
    leaks: list[str] = []
    for assignment in mapping.assignments:
        patterns = (
            f"{assignment.job_id.casefold()} version a is {assignment.version_a}",
            f"{assignment.job_id.casefold()} version b is {assignment.version_b}",
            f"version a = {assignment.version_a}",
            f"version b = {assignment.version_b}",
        )
        for pattern in patterns:
            if pattern in folded:
                leaks.append(pattern)
    return leaks
