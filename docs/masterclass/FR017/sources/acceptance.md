<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/eval/fr017_agent_evaluation_observability.md
Mode: full-file snapshot
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

# FR-017 — Agent Evaluation & Observability

**Status:** **Complete / Frozen / Accepted**  
**Date:** 2026-08-07  
**Documentation close-out:** 2026-08-07 (M4 freeze); repository consistency
close-out confirmed same day  
**Recommendation:** **ACCEPT AND FREEZE — FR-017 COMPLETE**  
**Binding product posture:** **narrow derive-only evaluation / learning substrate**  
**Engineering Learning Academy:** **Ready** — canonical engineering record =
this report; attachable package =
[masterclass/FR017/](../masterclass/FR017/) (`README.md`, `MANIFEST.md`, regenerable
`sources/`)  
**Next:** Horizon 1B (FR-018+) may proceed when the owner chooses — **not gated on
FR-017**. Ordinary prep remains `cic agent run`. Do not auto-start 1B in this close-out.

**ADR:** [ADR-009](../adr/009_orchestration_evaluation_substrate.md) (Accepted — M1–M4 close-out)

**Milestones (historical records):**
[M0](fr017_m0_engineering_spike.md) (Accepted),
[M1](fr017_m1_observability_contracts.md) (Accepted),
[M2](fr017_m2_corpus_reconstructability.md) (Accepted — GO),
[M3](fr017_m3_owner_cli.md) (Accepted),
[M4](fr017_m4_evaluation.md) (this freeze).

This document is the **canonical engineering record** for FR-017. Milestone reports
remain historical; do not reopen exit criteria without owner request.

---

## 1. Executive Summary

FR-017 delivers a **narrow derive-only orchestration evaluation capability**:

```text
Existing OrchestrationRun / Handoff / child AgentRun
        ↓
Deterministic metric derivation
        ↓
R1–R12 reconstructability evaluation
        ↓
Read-only owner CLI
        ↓
Operational / learning insight
```

| Layer | Delivered |
|-------|-----------|
| Contracts | `multi_agent.observability` (M1) |
| Corpus | 15/15 deterministic cases — **GO** (M2) |
| CLI | `cic agent orchestrate metrics` / `metrics-corpus` (M3) |
| Freeze | M4 acceptance + Academy package |

**Near-term commercial value is low.** Daily preparation is unchanged (`cic agent run`).
FR-017 does **not** justify dashboards or live telemetry at this stage. Value is
**audit reconstructability**, **honest missing-data semantics**, and **interview-
transferable evaluation engineering**.

**Horizon 1B remains unblocked.**

---

## 2. Business / engineering problem

After FR-016, orchestration audits exist but owners lacked a first-class way to:

1. reconstruct the authority story without reading source;
2. compare runs deterministically offline;
3. distinguish missing provider metadata from measured zero;
4. detect orphan / contradictory parent–child linkage.

FR-017 answers those needs **without** inventing a second SoT or an observability
product.

---

## 3. Final architecture

| Concern | Owner | FR-017 role |
|---------|-------|-------------|
| Workflow traces | FR-008 | None |
| Truth engine | FR-014 | Cite status only |
| BOPA metrics | FR-015 | Reuse `AgentRunMetrics` |
| Orchestration audits | FR-016 | Source records |
| Derive + R1–R12 + CLI | **FR-017** | Evaluation only |

**Invariant:** No DOS / BOPA / OBS / Handoff / AgentRun runtime changes; no new events;
no telemetry store; no dashboard.

**Package:** `career_intelligence.multi_agent.observability` (+ corpus + presentation)  
**CLI:** `cic agent orchestrate {metrics, metrics-corpus}` (+ existing FR-016 commands)

---

## 4. Final corpus results

| Metric | Value |
|--------|-------|
| Cases | **15/15 passed** |
| `go_no_go` | **GO** |
| Deterministic repeat | **True** |
| Runtime instrumentation required | **False** |

| Case | Result | Notes |
|------|--------|-------|
| C01 complete successful | PASS | Full R1–R12 |
| C02 delegation blocked | PASS | deny + stop |
| C03 BOPA child | PASS | provider/tokens present |
| C04 OBS brief | PASS | brief goal |
| C05 prepare_then_brief | PASS | both specialists |
| C06 missing optional metadata | PASS | `None` preserved |
| C07 measured zero | PASS | `0` ≠ missing |
| C08 orphaned child | PASS | R11 FAIL expected |
| C09 missing child join | PASS | ids correlate; tokens missing |
| C10 stale/incomplete handoff | PASS | reconstructable stale path |
| C11 safe resume | PASS | R12 + single visit |
| C12 loop stops | PASS | repeated / circular / no_progress |
| C13 provider unavailable | PASS | fail-closed stop |
| C14 contradictory audit | PASS | R7+R11 FAIL expected |
| C15 mixed aggregate | PASS | corpus roll-up |

Harness: `run_observability_corpus()` / `cic agent orchestrate metrics-corpus`.

---

## 5. R1–R12 results (normative behaviour)

| Id | Question (summary) | PASS means | FAIL means |
|----|--------------------|------------|------------|
| R1 | Owner goal | Goal kind + opportunity present | Missing goal identity |
| R2 | Observed state | `last_observation` + hash | No observation evidence |
| R3 | Selection | Allow/deny handoff or selection events | No selection evidence yet |
| R4 | DelegationPolicy | Allow/deny fields consistent | Inconsistent policy fields |
| R5 | Authority boundary | Target ∈ {obs, bopa} | Unknown target |
| R6 | Handoff lifecycle | Acceptance present | Missing acceptance |
| R7 | Child output | Completed allow cites expected child (stopped may omit) | Missing child refs |
| R8 | Stop reason | Present when not running | Terminal without stop |
| R9 | Owner next | Present when awaiting_owner | Awaiting without action |
| R10 | Limits | Limits visible | Invalid limit config |
| R11 | Parent/child walk | Correlation complete (or vacuous empty) | Orphans / gaps |
| R12 | Resume/idempotency | Hashes and/or keys (or early vacuous) | No resume evidence |

**Rules:** PASS requires evidence; FAIL names the gap; contradictions are surfaced
(C08/C14), never repaired; evaluation is deterministic.

---

## 6. Owner manual validation

Script: `scripts/run_fr017_m4_manual.py` — **PASSED** (2026-08-07).

| Demo | Evidence |
|------|----------|
| A | Persisted `prepare_then_brief` under disposable store; metrics CLI reconstructs full story; JSON unchanged |
| B | `--fixture C01` |
| C | `--fixture C05` |
| D | `--fixture C06` (`missing`) |
| E | `--fixture C07` (`0`) |
| F | `--fixture C08` (ORPHAN / R11 FAIL) |
| G | `--fixture C14` (R7+R11 FAIL) |
| H | `metrics-corpus` 15/15 GO |
| I | Read-only proof (A byte-identical; fixtures in-memory) |

Persisted reconstruction confirmed markers: goal → observed state → selection →
delegation → lifecycle → child → stop → owner next → limits → idempotency → R1–R12.

---

## 7. Metadata semantics

| Representation | Meaning |
|----------------|---------|
| `None` / display `missing` | Absent optional provider/model/token/cost/latency |
| `0` / `0.0` | Measured zero |
| Count `0` | Empty measurable count (handoffs, events, …) |

**Never** coerce missing → zero. C06/C07/C09/C15 prove the distinction.

---

## 8. Safety / read-only verification

- Metrics CLI loads only (`load` / `load_handoff` / optional agent `load`)
- Fixtures and corpus perform no store writes
- No DOS start/resume, no BOPA/OBS execution from FR-017 paths
- No pipeline mutation, submission, discovery, or truth waiver
- Unit proof: `test_cli_metrics_from_store_read_only`

---

## 9. Product-value assessment (honest)

| Question | Answer |
|----------|--------|
| Improve daily preparation? | **No** material improvement — prefer `cic agent run` |
| Materially improve Horizon 1B? | **No** — 1B not dependent on FR-017 |
| Useful operational insight? | **Yes** — reconstruct / debug orchestration audits |
| Improve audit/debugging? | **Yes** — R1–R12 + orphans + missing≠zero |
| Justify dashboards/telemetry now? | **No** |
| Remain narrow evaluation capability? | **Yes** |
| Future richer observability? | Only with failing evidence that derive-only cannot answer owner-critical questions at scale |

**Posture:** Low near-term commercial value. High learning / engineering-substrate value.

---

## 10. Learning outcomes (Academy)

1. Derive before instrument  
2. Observability ≠ dashboards  
3. Audit reconstructability as acceptance  
4. Missing versus zero  
5. Parent/child correlation and orphan detection  
6. Deterministic offline evaluation  
7. Source-of-truth boundaries (reuse FR-015; do not fork)  
8. Read-only evaluation surfaces  
9. Detect contradictions rather than repair them  
10. Avoid observability theatre  

---

## 11. Technical debt classification

| Item | Class |
|------|-------|
| Derive-only metrics + R1–R12 + CLI | **Accepted** (frozen) |
| Early-running R3 vacuity | **Accepted** limitation |
| Token/cost completeness offline | **Deferred** (null OK) |
| Metrics CLI polish / UX | **Deferred** |
| Dashboards / alerts / live tracing | **Out of Scope** |
| Telemetry backend / monitoring SaaS | **Out of Scope** |
| Richer time-travel replay | **Future FR** (if ever justified) |
| Fault-injection framework productisation | **Deferred** (patterns exist in corpus) |
| Horizon 1B integration | **Out of Scope** for FR-017; 1B separate |

---

## 12. Tests

| Suite | Path |
|-------|------|
| M1 contracts | `tests/unit/multi_agent/test_observability_m1.py` |
| M2 corpus | `tests/unit/multi_agent/test_observability_corpus_m2.py` |
| M3 CLI | `tests/unit/multi_agent/test_observability_cli_m3.py` |
| FR-016 regression | `tests/unit/multi_agent/test_cli_m3.py` |
| FR-015 regression | `tests/unit/agent/test_cli.py` |
| Manual M4 | `scripts/run_fr017_m4_manual.py` |

---

## 13. Documentation / Academy

Frozen navigation across README, AGENTS, roadmap, functional spec, domain model,
engineering principles, testing strategy, implementation notes, phase history,
changelog **1.110**, ADR-009 close-out.

Academy package: [masterclass/FR017/](../masterclass/FR017/) — regenerate:

```powershell
python scripts/build_masterclass_package.py FR017
```

---

## 14. Definition of Done

| Criterion | Status |
|-----------|--------|
| M0–M3 accepted | Yes |
| ADR-009 accepted | Yes |
| Final corpus green 15/15 | Yes |
| Owner manual validation | Yes |
| R1–R12 confirmed | Yes |
| Missing-versus-zero confirmed | Yes |
| No runtime mutation / no new SoT | Yes |
| Product assessment honest | Yes |
| Learning outcomes captured | Yes |
| Docs frozen | Yes |
| FR017 Masterclass package ready | Yes |
| Horizon 1B unblocked | Yes |
| No scope leakage | Yes |

---

## 15. Acceptance recommendation

**ACCEPT AND FREEZE — FR-017 COMPLETE**

---

## 16. Final repository status

| Item | Status |
|------|--------|
| FR-001–FR-016 | Frozen (unchanged) |
| FR-017 | **Complete / Frozen / Accepted** |
| Horizon 1A Stage 11 | Closed |
| Horizon 1B | **Not started; not blocked** |
| Daily prep | `cic agent run` |
