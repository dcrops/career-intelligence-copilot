"""FR-017 M2 — observability corpus reconstructability suite."""

from __future__ import annotations

from career_intelligence.multi_agent.observability_corpus import (
    CORPUS_CASE_IDS,
    go_no_go_observability,
    run_case_c06,
    run_case_c07,
    run_case_c08,
    run_case_c14,
    run_case_c15,
    run_observability_corpus,
)


def test_corpus_case_ids_cover_fifteen() -> None:
    assert len(CORPUS_CASE_IDS) == 15


def test_run_observability_corpus_all_pass_go() -> None:
    report = run_observability_corpus()
    assert report.total == 15
    assert report.passed == 15
    assert report.all_passed is True
    assert report.deterministic_repeat_ok is True
    assert report.derive_only is True
    assert report.runtime_instrumentation_required is False
    assert report.go_no_go == "GO"
    assert {r.case_id for r in report.results} == set(CORPUS_CASE_IDS)
    failed = [r.case_id for r in report.results if not r.passed]
    assert failed == []


def test_go_no_go_helper() -> None:
    verdict, rationale = go_no_go_observability()
    assert verdict == "GO"
    assert "derive-only" in rationale


def test_missing_versus_zero_cases() -> None:
    missing = run_case_c06()
    zero = run_case_c07()
    assert missing.passed and missing.missing_vs_zero_ok
    assert zero.passed and zero.missing_vs_zero_ok
    assert missing.metrics[0].input_tokens is None
    assert zero.metrics[0].input_tokens == 0


def test_orphan_and_malformed_fail_r11() -> None:
    orphan = run_case_c08()
    malformed = run_case_c14()
    assert orphan.passed
    assert malformed.passed
    assert "R11" in orphan.actual_r_failures
    assert "R11" in malformed.actual_r_failures
    assert orphan.correlations[0].correlation_complete is False
    assert malformed.correlations[0].correlation_complete is False


def test_mixed_corpus_aggregation() -> None:
    result = run_case_c15()
    assert result.passed
    assert result.corpus_aggregate is not None
    assert result.corpus_aggregate.run_count == 8
    assert result.corpus_aggregate.provider_unavailable_count == 1
    assert result.missing_vs_zero_ok is True


def test_deterministic_repeatability_metric_dumps() -> None:
    a = run_observability_corpus()
    b = run_observability_corpus()
    for ra, rb in zip(a.results, b.results, strict=True):
        assert ra.case_id == rb.case_id
        assert ra.passed == rb.passed
        assert tuple(m.model_dump(mode="json") for m in ra.metrics) == tuple(
            m.model_dump(mode="json") for m in rb.metrics
        )
        assert tuple(r.model_dump(mode="json") for r in ra.reconstructability) == tuple(
            r.model_dump(mode="json") for r in rb.reconstructability
        )
