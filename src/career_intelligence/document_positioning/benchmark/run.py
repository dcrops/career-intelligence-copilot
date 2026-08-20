"""Orchestrate the frozen M5 benchmark. Stop at the owner-review gate."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from random import Random, SystemRandom

from career_intelligence.document_positioning.benchmark.baseline import (
    FixtureBaselineComposer,
    OpenAIBaselineComposer,
    generate_baseline_documents,
)
from career_intelligence.document_positioning.benchmark.cic import (
    CicComposers,
    generate_cic_documents,
    live_cic_composers,
)
from career_intelligence.document_positioning.benchmark.evidence import (
    FactualEvidenceBundle,
    baseline_payload,
    build_factual_evidence_bundle,
    bundle_hash,
    payload_contains_cic_policy,
)
from career_intelligence.document_positioning.benchmark.jobs import (
    CAREER_PROFILE_PATH,
    FROZEN_EVAL_JOBS,
    FrozenEvalJob,
    load_job_analysis,
)
from career_intelligence.document_positioning.benchmark.mapping import (
    BlindMapping,
    build_blind_mapping,
    persist_mapping,
)
from career_intelligence.document_positioning.benchmark.protocol import (
    GenerationProtocol,
)
from career_intelligence.document_positioning.benchmark.render import (
    chrome_leak_hits,
    write_owner_review,
)
from career_intelligence.document_positioning.benchmark.retries import RetryExhaustedError
from career_intelligence.document_positioning.benchmark.truth import (
    TruthPairRecord,
    evaluate_document_pair,
)
from career_intelligence.document_positioning.cv_composer import FixtureCvPositioningComposer
from career_intelligence.document_positioning.letter_composer import (
    FixtureCoverLetterPositioningComposer,
)
from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile

DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[4] / "docs" / "eval" / "document_positioning_m5"
)


class BenchmarkBlockedError(RuntimeError):
    pass


def load_openai_api_key(repo: Path) -> str | None:
    existing = os.getenv("OPENAI_API_KEY")
    if existing:
        return existing
    secrets = repo / "config" / "local_secrets.env"
    if not secrets.is_file():
        return None
    for line in secrets.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "OPENAI_API_KEY":
            return value.strip().strip('"').strip("'")
    return None


def fixture_cic_composers() -> CicComposers:
    return CicComposers(
        FixtureCvPositioningComposer(),
        FixtureCoverLetterPositioningComposer(),
        cv_model="fixture",
        letter_model="fixture",
        temperature=0.0,
    )


def run_benchmark(
    output_dir: Path,
    *,
    profile: CareerProfile | None = None,
    cic_composers: CicComposers | None = None,
    baseline_composer: OpenAIBaselineComposer | FixtureBaselineComposer | None = None,
    rng: Random | None = None,
    jobs: tuple[FrozenEvalJob, ...] = FROZEN_EVAL_JOBS,
    live: bool = False,
) -> dict[str, object]:
    """Generate A/B documents and owner artefacts. Does not reveal the mapping."""
    if live:
        if cic_composers is None:
            cic_composers = live_cic_composers()
        if baseline_composer is None:
            baseline_composer = OpenAIBaselineComposer()
        if rng is None:
            rng = SystemRandom()
    else:
        if cic_composers is None:
            cic_composers = fixture_cic_composers()
        if baseline_composer is None:
            baseline_composer = FixtureBaselineComposer()
        if rng is None:
            rng = Random(0)

    bound_profile = profile or CareerProfileService.from_path(CAREER_PROFILE_PATH).load()
    protocol = GenerationProtocol()
    owner_dir = output_dir / "owner_review"
    hidden_dir = output_dir / "hidden"
    records_dir = hidden_dir / "generation_records"
    records_dir.mkdir(parents=True, exist_ok=True)

    bundles: dict[str, FactualEvidenceBundle] = {}
    hashes: dict[str, str] = {}
    for job in jobs:
        bundle = build_factual_evidence_bundle(job, profile=bound_profile)
        leaks = payload_contains_cic_policy(baseline_payload(bundle))
        if leaks:
            raise BenchmarkBlockedError(
                f"{job.job_id} baseline payload contains CIC policy keys: {leaks}"
            )
        digest = bundle_hash(bundle)
        bundles[job.job_id] = bundle
        hashes[job.job_id] = digest
        (records_dir / f"{job.job_id}_factual_bundle.json").write_text(
            bundle.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

    cic_records = {}
    baseline_records = {}
    documents: dict[str, dict[str, tuple[str, str]]] = {}
    truth_records: dict[str, dict[str, TruthPairRecord]] = {}

    for job in jobs:
        bundle = bundles[job.job_id]
        try:
            cic_record, _, _ = generate_cic_documents(
                job, bound_profile, cic_composers
            )
            baseline_record, _ = generate_baseline_documents(
                bundle, baseline_composer
            )
        except RetryExhaustedError as error:
            (records_dir / f"{job.job_id}_generation_failure.json").write_text(
                json.dumps(
                    {
                        "job_id": job.job_id,
                        "error": str(error),
                        "attempts": error.attempts,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            raise BenchmarkBlockedError(
                f"{job.job_id} generation failed under the frozen retry policy: {error}"
            ) from error
        cic_records[job.job_id] = cic_record
        baseline_records[job.job_id] = baseline_record
        documents[job.job_id] = {
            "cic": (cic_record.cv_markdown, cic_record.letter_markdown),
            "baseline": (baseline_record.cv_markdown, baseline_record.letter_markdown),
        }
        analysis = load_job_analysis(job)
        context = [item.name for item in analysis.technologies]
        cic_truth = evaluate_document_pair(
            job_id=job.job_id,
            system="hidden",
            cv_markdown=cic_record.cv_markdown,
            letter_markdown=cic_record.letter_markdown,
            profile=bound_profile,
            context_technology_labels=context,
        )
        baseline_truth = evaluate_document_pair(
            job_id=job.job_id,
            system="hidden",
            cv_markdown=baseline_record.cv_markdown,
            letter_markdown=baseline_record.letter_markdown,
            profile=bound_profile,
            context_technology_labels=context,
        )
        # Persist system identity only under hidden/.
        cic_truth = cic_truth.model_copy(update={"system": "cic"})
        baseline_truth = baseline_truth.model_copy(update={"system": "baseline"})
        truth_records[job.job_id] = {"cic": cic_truth, "baseline": baseline_truth}
        (records_dir / f"{job.job_id}_cic.json").write_text(
            cic_record.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        (records_dir / f"{job.job_id}_baseline.json").write_text(
            baseline_record.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        (records_dir / f"{job.job_id}_truth.json").write_text(
            json.dumps(
                {
                    "cic": cic_truth.model_dump(mode="json"),
                    "baseline": baseline_truth.model_dump(mode="json"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    mapping = build_blind_mapping(tuple(job.job_id for job in jobs), rng=rng)
    persist_mapping(mapping, hidden_dir)
    write_owner_review(
        owner_dir=owner_dir,
        jobs=jobs,
        bundles=bundles,
        mapping=mapping,
        documents=documents,
    )
    _assert_owner_chrome_clean(owner_dir, mapping)

    timestamp = datetime.now(tz=UTC).isoformat()
    protocol_payload = {
        "protocol": protocol.model_dump(mode="json"),
        "evaluated_at": timestamp,
        "live": live,
        "job_ids": [job.job_id for job in jobs],
        "evidence_bundle_hashes": hashes,
        "mapping_revealed": False,
        "owner_scoring_complete": False,
        "post_hoc_tuning": False,
        "production_prepare_wired": False,
        "csk_live_package_regenerated": False,
        "seek_playwright_aas_run": False,
        "m6_started": False,
        "previous_run_invalidated": "INVALIDATED — PRE-BENCHMARK PRODUCT BLOCKER",
    }
    (records_dir / "protocol.json").write_text(
        json.dumps(protocol_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "output_dir": str(output_dir),
        "owner_dir": str(owner_dir),
        "hidden_dir": str(hidden_dir),
        "evaluated_at": timestamp,
        "evidence_bundle_hashes": hashes,
        "mapping": mapping,
        "truth": {
            job_id: {
                system: record.model_dump(mode="json")
                for system, record in pair.items()
            }
            for job_id, pair in truth_records.items()
        },
        "live": live,
    }


def _assert_owner_chrome_clean(owner_dir: Path, mapping: BlindMapping) -> None:
    from career_intelligence.document_positioning.benchmark.mapping import (
        mapping_leaks_in_text,
    )

    for path in owner_dir.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "owner_scores.json":
            continue
        if path.name.endswith("_cv.md") or path.name.endswith("_letter.md"):
            continue
        if path.name == "comparison.md":
            continue
        leaks = chrome_leak_hits(text) + mapping_leaks_in_text(text, mapping)
        if leaks:
            raise BenchmarkBlockedError(
                f"Owner artefact leaked generator identity in {path}: {leaks}"
            )
