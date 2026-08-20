"""Frozen M5 evaluation protocol constants.

These values were frozen in M0 and must not change after seeing results.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobId = Literal["E1", "E2", "E3", "E4"]
SystemId = Literal["cic", "baseline"]
VersionLabel = Literal["A", "B"]
Preference = Literal["preferred", "tied", "weaker"]
OverallDecision = Literal["version_a", "version_b", "tie"]
SystemDecision = Literal["cic", "baseline", "tie"]

RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "scan_15s",
    "role_positioning",
    "evidence_selection",
    "transfer_argument",
    "honest_gaps",
    "specificity",
    "clarity",
    "concision",
    "overall_submit_preference",
)

RELEASE_MIN_CIC_PREFERRED_OR_TIED = 3
RELEASE_JOB_COUNT = 4

CIC_CV_MODEL = "gpt-4o-mini"
CIC_LETTER_MODEL = "gpt-4o-mini"
CIC_TEMPERATURE = 0.2
BASELINE_MODEL = "gpt-4o"
BASELINE_TEMPERATURE = 0.2
BASELINE_PROMPT_VERSION = "v1"

# One initial attempt plus this many retries for provider / structured-output
# / local-validation failure only. Never retry to improve comparative quality.
MAX_PROVIDER_RETRIES = 2
PROVIDER_TIMEOUT_SECONDS = 120.0

CIC_POLICY_KEYS: frozenset[str] = frozenset(
    {
        "argument_spine",
        "selected_evidence_refs",
        "selected_highlights",
        "selected_projects",
        "selected_sources",
        "portfolio_overrides",
        "opening_facts",
        "body_facts",
        "closing_facts",
        "trajectory_mode",
        "include_methodology",
        "high_priority_needs",
        "evidence_count_policy",
    }
)

OWNER_CHROME_LEAK_TOKENS: tuple[str, ...] = (
    "cic",
    "baseline",
    "openai",
    "gpt-4",
    "gpt-4o",
    "positioningplan",
    "bounded composer",
    "m3 positioned",
    "m4 positioned",
    "fixture composer",
    "system a is",
    "system b is",
)

GENERATION_PROTOCOL_ID = "document_positioning_m5_v1"
BENCHMARK_RUN_ID = "m5_restart_after_m3_optional_relevance_2026-08-20"


class RetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_retries: int = MAX_PROVIDER_RETRIES
    retry_on: tuple[str, ...] = (
        "provider_error",
        "structured_output_error",
        "local_validation_error",
    )
    retry_on_quality: Literal[False] = False
    applied_symmetrically: Literal[True] = True


class GenerationProtocol(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_id: str = GENERATION_PROTOCOL_ID
    benchmark_run_id: str = BENCHMARK_RUN_ID
    cic_cv_model: str = CIC_CV_MODEL
    cic_letter_model: str = CIC_LETTER_MODEL
    cic_temperature: float = CIC_TEMPERATURE
    baseline_model: str = BASELINE_MODEL
    baseline_temperature: float = BASELINE_TEMPERATURE
    baseline_prompt_version: str = BASELINE_PROMPT_VERSION
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    release_min_cic_preferred_or_tied: int = RELEASE_MIN_CIC_PREFERRED_OR_TIED
    release_job_count: int = RELEASE_JOB_COUNT
    cic_truth_failures_allowed: int = 0
    notes: str = (
        "A uses implemented M3/M4 bounded OpenAI composers, unwired from "
        "cic package prepare. B independently positions from the same factual "
        "evidence bundle and the same truth boundaries. B does not receive CIC "
        "selection decisions or argument spine. No post-hoc tuning."
    )
