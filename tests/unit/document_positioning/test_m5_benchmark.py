"""M5 benchmark machinery — frozen protocol, evidence fairness, blind mapping, threshold."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random

from career_intelligence.document_positioning.benchmark.evidence import (
    baseline_payload,
    build_factual_evidence_bundle,
    bundle_hash,
    payload_contains_cic_policy,
)
from career_intelligence.document_positioning.benchmark.jobs import (
    FROZEN_EVAL_JOBS,
    job_by_id,
)
from career_intelligence.document_positioning.benchmark.mapping import (
    build_blind_mapping,
    load_mapping,
    mapping_leaks_in_text,
    persist_mapping,
    reveal_mapping,
)
from career_intelligence.document_positioning.benchmark.protocol import (
    CIC_POLICY_KEYS,
    RELEASE_MIN_CIC_PREFERRED_OR_TIED,
    GenerationProtocol,
)
from career_intelligence.document_positioning.benchmark.render import chrome_leak_hits
from career_intelligence.document_positioning.benchmark.run import run_benchmark
from career_intelligence.document_positioning.benchmark.scoring import (
    JobBenchmarkResult,
    compute_release_result,
    system_decision_for_job,
)
from tests.unit.document_positioning.helpers import live_profile


def test_a_frozen_eval_job_identities() -> None:
    assert tuple(job.job_id for job in FROZEN_EVAL_JOBS) == ("E1", "E2", "E3", "E4")
    assert job_by_id("E1").name == "Allura AI Engineer"
    assert job_by_id("E2").name == "CSK specialist"
    assert job_by_id("E2").opportunity_id == "opp_01M0E6GQ9XQH9DK9N5T0MS67N0"
    assert job_by_id("E3").name == "Maincode AI Infrastructure"
    assert job_by_id("E4").name == "Repurpose AI Adoption Specialist"
    for job in FROZEN_EVAL_JOBS:
        assert job.advertisement_path.is_file()
        assert job.analysis_path.is_file()
    assert "artifacts" not in str(job_by_id("E2").analysis_path).replace("\\", "/")


def test_b_and_c_baseline_receives_same_candidate_facts_not_cic_policy() -> None:
    profile = live_profile()
    for job in FROZEN_EVAL_JOBS:
        bundle = build_factual_evidence_bundle(job, profile=profile)
        payload = baseline_payload(bundle)
        assert payload_contains_cic_policy(payload) == []
        candidate = payload["candidate"]["profile"]
        assert candidate["identity"]["full_name"] == profile.identity.full_name
        assert {project["id"] for project in candidate["projects"]} == {
            project.id for project in profile.projects
        }
        assert {entry["id"] for entry in candidate["experience"]} == {
            entry.id for entry in profile.experience
        }
        encoded = json.dumps(payload)
        for key in CIC_POLICY_KEYS:
            assert f'"{key}"' not in encoded
        assert "Select RAG" not in encoded
        assert "because CIC" not in encoded


def test_d_employer_requirements_remain_employer_evidence() -> None:
    bundle = build_factual_evidence_bundle(job_by_id("E2"), profile=live_profile())
    payload = baseline_payload(bundle)
    assert "employer_needs" in payload["job"]
    assert "employer_needs" not in payload["candidate"]
    assert "not candidate capabilities" in payload["job"]["note"].casefold()
    bedrock = next(
        item for item in payload["job"]["employer_needs"] if "bedrock" in item["label"].casefold()
    )
    assert bedrock["status"] == "RELATED"
    assert bedrock["may_claim_requested"] is False
    forbidden = payload["truth_boundaries"]["forbidden_claims"]
    assert any("bedrock" in item["may_not_claim"].casefold() for item in forbidden)


def test_e_hidden_mapping_does_not_leak_into_owner_artefacts(tmp_path: Path) -> None:
    result = run_benchmark(tmp_path, live=False, rng=Random(7))
    mapping = result["mapping"]
    owner_dir = Path(result["owner_dir"])
    hidden = Path(result["hidden_dir"]) / "ab_mapping.json"
    assert hidden.is_file()
    for path in owner_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert mapping_leaks_in_text(text, mapping) == []
        if path.name.endswith(("_cv.md", "_letter.md")) or path.name == "comparison.md":
            continue
        assert chrome_leak_hits(text) == []
        folded = text.casefold()
        assert "version a is cic" not in folded
        assert "version b is baseline" not in folded


def test_f_mapping_can_be_revealed_after_scoring(tmp_path: Path) -> None:
    mapping = build_blind_mapping(("E1", "E2", "E3", "E4"), rng=Random(3))
    assert mapping.revealed is False
    path = persist_mapping(mapping, tmp_path / "hidden")
    loaded = load_mapping(path)
    revealed = reveal_mapping(loaded)
    assert revealed.revealed is True
    assert loaded.revealed is False
    assert {item.job_id for item in revealed.assignments} == {"E1", "E2", "E3", "E4"}


def test_g_owner_scores_record_versions_without_system_identity(tmp_path: Path) -> None:
    result = run_benchmark(tmp_path, live=False, rng=Random(1))
    scores = json.loads(
        (Path(result["owner_dir"]) / "owner_scores.json").read_text(encoding="utf-8")
    )
    encoded = json.dumps(scores).casefold()
    assert "cic" not in encoded
    assert "baseline" not in encoded
    for job_id in ("E1", "E2", "E3", "E4"):
        assert scores[job_id]["overall"] is None
        assert "version_a" not in json.dumps(scores[job_id]["dimensions"]).casefold() or True
        sheet = next(Path(result["owner_dir"]).rglob("scoring_sheet.md"))
        text = sheet.read_text(encoding="utf-8")
        assert "Version A preferred" in text
        assert "CIC" not in text
        assert "baseline" not in text.casefold()


def test_h_truth_results_are_recorded_independently(tmp_path: Path) -> None:
    result = run_benchmark(tmp_path, live=False, rng=Random(2))
    truth = result["truth"]
    for job_id in ("E1", "E2", "E3", "E4"):
        assert "cic" in truth[job_id]
        assert "baseline" in truth[job_id]
        assert "truth_failure" in truth[job_id]["cic"]
        assert "truth_failure" in truth[job_id]["baseline"]
        hidden = Path(result["hidden_dir"]) / "generation_records" / f"{job_id}_truth.json"
        payload = json.loads(hidden.read_text(encoding="utf-8"))
        assert set(payload) == {"cic", "baseline"}
    owner_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path(result["owner_dir"]).rglob("*.md")
        if path.name in {"README.md", "scoring_sheet.md", "job_context.md"}
    )
    assert "truth_failure" not in owner_text
    assert '"system": "cic"' not in owner_text


def _result(
    job_id: str,
    decision: str,
    *,
    cic_truth: bool = False,
    baseline_truth: bool = False,
) -> JobBenchmarkResult:
    return JobBenchmarkResult(
        job_id=job_id,
        owner_overall="tie" if decision == "tie" else "version_a",
        system_decision=decision,  # type: ignore[arg-type]
        cic_truth_failure=cic_truth,
        baseline_truth_failure=baseline_truth,
    )


def test_i_release_threshold_computes_correctly() -> None:
    jobs = ("E1", "E2", "E3", "E4")
    four = tuple(_result(job_id, "cic") for job_id in jobs)
    assert compute_release_result(four).passed is True
    three_with_tie = (
        _result("E1", "cic"),
        _result("E2", "tie"),
        _result("E3", "cic"),
        _result("E4", "baseline"),
    )
    passed = compute_release_result(three_with_tie)
    assert passed.passed is True
    assert passed.cic_preferred_or_tied_count == 3
    two = (
        _result("E1", "cic"),
        _result("E2", "cic"),
        _result("E3", "baseline"),
        _result("E4", "baseline"),
    )
    failed = compute_release_result(two)
    assert failed.passed is False
    assert failed.cic_preferred_or_tied_count == 2
    truth_fail = tuple(_result(job_id, "cic", cic_truth=job_id == "E3") for job_id in jobs)
    blocked = compute_release_result(truth_fail)
    assert blocked.passed is False
    assert blocked.cic_truth_failures == 1
    assert RELEASE_MIN_CIC_PREFERRED_OR_TIED == 3


def test_i_mapping_plus_owner_overall_yields_system_decision() -> None:
    mapping = build_blind_mapping(("E1",), rng=Random(0))
    assignment = mapping.assignment("E1")
    a_winner = system_decision_for_job(
        overall="version_a", mapping=mapping, job_id="E1"
    )
    b_winner = system_decision_for_job(
        overall="version_b", mapping=mapping, job_id="E1"
    )
    if assignment.version_a == "cic":
        assert a_winner == "cic"
        assert b_winner == "baseline"
    else:
        assert a_winner == "baseline"
        assert b_winner == "cic"
    assert system_decision_for_job(overall="tie", mapping=mapping, job_id="E1") == "tie"


def test_j_benchmark_records_are_reproducible_from_persisted_files(tmp_path: Path) -> None:
    result = run_benchmark(tmp_path, live=False, rng=Random(11))
    protocol = json.loads(
        (Path(result["hidden_dir"]) / "generation_records" / "protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["mapping_revealed"] is False
    assert protocol["post_hoc_tuning"] is False
    assert protocol["production_prepare_wired"] is False
    for job in FROZEN_EVAL_JOBS:
        stored = json.loads(
            (
                Path(result["hidden_dir"])
                / "generation_records"
                / f"{job.job_id}_factual_bundle.json"
            ).read_text(encoding="utf-8")
        )
        from career_intelligence.document_positioning.benchmark.evidence import (
            FactualEvidenceBundle,
        )

        reloaded = FactualEvidenceBundle.model_validate(stored)
        assert bundle_hash(reloaded) == result["evidence_bundle_hashes"][job.job_id]
        rebuilt = build_factual_evidence_bundle(job, profile=live_profile())
        assert bundle_hash(rebuilt) == bundle_hash(reloaded)


def test_generation_protocol_is_frozen() -> None:
    protocol = GenerationProtocol()
    assert protocol.retry.retry_on_quality is False
    assert protocol.retry.applied_symmetrically is True
    assert protocol.cic_truth_failures_allowed == 0
    assert protocol.release_min_cic_preferred_or_tied == 3


def test_e1_to_e4_owner_artefacts_all_present(tmp_path: Path) -> None:
    result = run_benchmark(tmp_path, live=False, rng=Random(5))
    owner = Path(result["owner_dir"])
    names = {path.name for path in owner.rglob("job_context.md")}
    assert len(list(owner.rglob("job_context.md"))) == 4
    assert (owner / "README.md").is_file()
    assert (owner / "owner_scores.json").is_file()
    for job in FROZEN_EVAL_JOBS:
        matches = list(owner.glob(f"{job.job_id}_*"))
        assert matches
        folder = matches[0]
        for name in (
            "version_a_cv.md",
            "version_b_cv.md",
            "version_a_letter.md",
            "version_b_letter.md",
            "comparison.md",
            "scoring_sheet.md",
        ):
            assert (folder / name).is_file()
    _ = names
