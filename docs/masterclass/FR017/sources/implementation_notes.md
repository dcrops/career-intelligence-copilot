<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/08_implementation_notes.md
Mode: section snapshot ('## FR-017 M0 — Evaluation & observability spike (document-only)' → None)
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

## FR-017 M0 — Evaluation & observability spike (document-only)

**Date:** 2026-08-07  
**Eval:** [eval/fr017_m0_engineering_spike.md](eval/fr017_m0_engineering_spike.md)

Narrow GO accepted: derive-only orchestration metrics; reconstructability R1–R12;
no dashboards; **Horizon 1B not blocked on FR-017**.

## FR-017 M1 — Observability contracts

**Date:** 2026-08-07  
**Eval:** [eval/fr017_m1_observability_contracts.md](eval/fr017_m1_observability_contracts.md)  
**ADR:** [ADR-009](adr/009_orchestration_evaluation_substrate.md)

`multi_agent.observability` derive API; R1–R12 helpers; missing≠zero; unit tests.
No DOS/BOPA/OBS changes.

## FR-017 M2 — Corpus reconstructability

**Date:** 2026-08-07  
**Eval:** [eval/fr017_m2_corpus_reconstructability.md](eval/fr017_m2_corpus_reconstructability.md)

15/15 deterministic corpus **GO**; correlation/orphan; aggregates; repeatability.

## FR-017 M3 — Read-only metrics CLI

**Date:** 2026-08-07  
**Eval:** [eval/fr017_m3_owner_cli.md](eval/fr017_m3_owner_cli.md)

`cic agent orchestrate metrics` / `metrics-corpus`; fixture demos; presentation.

## FR-017 M4 — Evaluation and documentation freeze

**Date:** 2026-08-07  
**Eval:** [eval/fr017_m4_evaluation.md](eval/fr017_m4_evaluation.md)  
**Acceptance:** [eval/fr017_agent_evaluation_observability.md](eval/fr017_agent_evaluation_observability.md)

Final corpus + owner validation; product/learning honesty; docs freeze; Academy
package. Binding posture: narrow derive-only; Horizon 1B unblocked.

**Manual:** `scripts/run_fr017_m4_manual.py`  
**Tests:** `tests/unit/multi_agent/test_observability_*.py`  
**Academy package:** [masterclass/FR017/](masterclass/FR017/) — regenerate with
`python scripts/build_masterclass_package.py FR017`
