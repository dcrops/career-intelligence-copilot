"""M5 release-threshold calculation. Do not reinterpret after seeing results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from career_intelligence.document_positioning.benchmark.mapping import BlindMapping
from career_intelligence.document_positioning.benchmark.protocol import (
    RELEASE_JOB_COUNT,
    RELEASE_MIN_CIC_PREFERRED_OR_TIED,
    OverallDecision,
    SystemDecision,
)


class JobOwnerScore(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    job_id: str
    overall: OverallDecision
    dimensions: dict[str, OverallDecision | None] = Field(default_factory=dict)
    notes: dict[str, str] = Field(default_factory=dict)


class JobBenchmarkResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    owner_overall: OverallDecision
    system_decision: SystemDecision
    cic_truth_failure: bool
    baseline_truth_failure: bool


class BenchmarkReleaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cic_preferred_jobs: tuple[str, ...]
    baseline_preferred_jobs: tuple[str, ...]
    tie_jobs: tuple[str, ...]
    cic_preferred_or_tied_count: int
    cic_truth_failures: int
    baseline_truth_failures: int
    passed: bool
    reason: str


def system_decision_for_job(
    *,
    overall: OverallDecision,
    mapping: BlindMapping,
    job_id: str,
) -> SystemDecision:
    if overall == "tie":
        return "tie"
    if overall == "version_a":
        winner = mapping.system_for(job_id, "A")
    elif overall == "version_b":
        winner = mapping.system_for(job_id, "B")
    else:
        raise ValueError(f"Unknown overall decision: {overall}")
    return winner


def compute_release_result(
    job_results: tuple[JobBenchmarkResult, ...],
) -> BenchmarkReleaseResult:
    if len(job_results) != RELEASE_JOB_COUNT:
        raise ValueError(
            f"Release calculation requires {RELEASE_JOB_COUNT} jobs, "
            f"got {len(job_results)}"
        )
    cic_pref = tuple(
        item.job_id for item in job_results if item.system_decision == "cic"
    )
    baseline_pref = tuple(
        item.job_id for item in job_results if item.system_decision == "baseline"
    )
    ties = tuple(item.job_id for item in job_results if item.system_decision == "tie")
    cic_ok = len(cic_pref) + len(ties)
    cic_truth = sum(1 for item in job_results if item.cic_truth_failure)
    baseline_truth = sum(1 for item in job_results if item.baseline_truth_failure)
    passed = (
        cic_ok >= RELEASE_MIN_CIC_PREFERRED_OR_TIED
        and cic_truth == 0
    )
    if cic_truth:
        reason = (
            f"FAIL: CIC Truth failures = {cic_truth} (zero allowed). "
            f"CIC preferred or tied on {cic_ok}/{RELEASE_JOB_COUNT}."
        )
    elif passed:
        reason = (
            f"PASS: CIC preferred or tied on {cic_ok}/{RELEASE_JOB_COUNT} "
            "and CIC Truth failures = 0."
        )
    else:
        reason = (
            f"FAIL: CIC preferred or tied on {cic_ok}/{RELEASE_JOB_COUNT}; "
            f"threshold is {RELEASE_MIN_CIC_PREFERRED_OR_TIED}/{RELEASE_JOB_COUNT}. "
            "CSK-only success is not acceptance."
        )
    return BenchmarkReleaseResult(
        cic_preferred_jobs=cic_pref,
        baseline_preferred_jobs=baseline_pref,
        tie_jobs=ties,
        cic_preferred_or_tied_count=cic_ok,
        cic_truth_failures=cic_truth,
        baseline_truth_failures=baseline_truth,
        passed=passed,
        reason=reason,
    )
