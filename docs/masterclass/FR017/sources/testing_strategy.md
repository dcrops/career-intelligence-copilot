<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/07_testing_strategy.md
Mode: section snapshot ('### FR-017 coverage (M1–M4 — frozen)' → '### FR-018 coverage (M1–M4 — frozen)')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

### FR-017 coverage (M1–M4 — frozen)

| Area | Coverage |
|------|----------|
| Contracts | OrchestrationRunMetrics; R1–R12; missing≠zero; parent/child correlation |
| Corpus | 15/15 deterministic fixtures; go/no-go GO |
| CLI (M3) | `cic agent orchestrate metrics` / `metrics-corpus`; fixtures |
| Evaluation (M4) | Final corpus; owner validation; product-value honesty; freeze |
| Unit | `tests/unit/multi_agent/test_observability_*.py` |
| Manual | `scripts/run_fr017_m3_manual.py`, `run_fr017_m4_manual.py` |
| Acceptance | [eval/fr017_agent_evaluation_observability.md](eval/fr017_agent_evaluation_observability.md) |
