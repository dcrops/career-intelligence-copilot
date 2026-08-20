"""M5 frozen quality benchmark machinery. Evaluation only; not production wiring."""

from .baseline import (
    BaselineDocuments,
    FixtureBaselineComposer,
    OpenAIBaselineComposer,
    generate_baseline_documents,
)
from .cic import CicComposers, generate_cic_documents, live_cic_composers
from .evidence import (
    FactualEvidenceBundle,
    baseline_payload,
    build_factual_evidence_bundle,
    bundle_hash,
    payload_contains_cic_policy,
)
from .jobs import FROZEN_EVAL_JOBS, FrozenEvalJob, job_by_id
from .mapping import BlindMapping, build_blind_mapping, reveal_mapping
from .protocol import GenerationProtocol
from .run import fixture_cic_composers, run_benchmark
from .scoring import compute_release_result
from .truth import evaluate_document_pair

__all__ = [
    "BaselineDocuments",
    "BlindMapping",
    "CicComposers",
    "FROZEN_EVAL_JOBS",
    "FactualEvidenceBundle",
    "FixtureBaselineComposer",
    "FrozenEvalJob",
    "GenerationProtocol",
    "OpenAIBaselineComposer",
    "baseline_payload",
    "build_blind_mapping",
    "build_factual_evidence_bundle",
    "bundle_hash",
    "compute_release_result",
    "evaluate_document_pair",
    "fixture_cic_composers",
    "generate_baseline_documents",
    "generate_cic_documents",
    "job_by_id",
    "live_cic_composers",
    "payload_contains_cic_policy",
    "reveal_mapping",
    "run_benchmark",
]
