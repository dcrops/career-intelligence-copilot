# FR-017 M2 — Corpus Reconstructability & Deterministic Evaluation

**Status:** **Complete (M2)** — **GO** (derive-only; reconstructability reliable)
(**Accepted** — unlocked M3); FR-017 later **Complete / Frozen** —
[fr017_agent_evaluation_observability.md](fr017_agent_evaluation_observability.md)  
**Date:** 2026-08-07  
**Phase:** Horizon 1A Stage 11  
**Architecture:** [ADR-009](../adr/009_orchestration_evaluation_substrate.md)  
**Preceding:** [M1 contracts](fr017_m1_observability_contracts.md) (**Accepted**);
[M0 spike](fr017_m0_engineering_spike.md) (**Accepted**)  
**Succeeded by:** [M3 owner CLI](fr017_m3_owner_cli.md) (**Complete**)  
**Does not begin:** M4 freeze, dashboards, telemetry stores, tracing platforms, DOS /
BOPA / OBS / orchestration runtime changes, Horizon 1B.

---

## 1. Executive summary

M2 packages a **deterministic, derive-only** observability corpus over static
`OrchestrationRun` / `Handoff` / optional `AgentRunMetrics` fixtures. It exercises
M1 metrics, parent/child correlation, orphan detection, missing-vs-zero semantics,
R1–R12 reconstructability, and mixed-corpus aggregation — **without** invoking DOS,
BOPA, OBS, or adding events/SoTs.

| Signal | Result |
|--------|--------|
| Cases | **15/15 passed** |
| Deterministic repeat | **Yes** |
| Runtime instrumentation required | **No** |
| FR-016 redesign required | **No** |
| Horizon 1B blocked | **No** |
| **Go / no-go** | **GO** |

Useful evaluation remains derive-only. Reconstructability is reliable from existing
records. **Do not DEFER FR-017** on instrumentation grounds.

---

## 2. Corpus design

Module: `career_intelligence.multi_agent.observability_corpus`  
API: `run_observability_corpus()` → `ObservabilityCorpusReport`

Fixtures use **fixed ULID ids and timestamps** so dumps are byte-stable across runs.
No supervisor execution; no live LLM; no store I/O.

| Case | Intent |
|------|--------|
| C01 | Complete successful OBS run |
| C02 | Delegation blocked (deny + `delegation_blocked`) |
| C03 | BOPA child run with provider/token/cost |
| C04 | OBS brief (`brief` goal) |
| C05 | `prepare_then_brief` — BOPA + OBS outputs |
| C06 | Missing optional provider/model/token/cost/latency (`None`) |
| C07 | Measured zero distinguished from missing |
| C08 | Orphaned child reference (parent ≠ handoff) |
| C09 | Missing child `AgentRunMetrics` join (ids present) |
| C10 | Stale / incomplete handoff (`handoff_stale`) |
| C11 | Safe resume — hash change + idempotency; single visit |
| C12 | Loop stops: `repeated_delegation`, `circular_delegation`, `no_progress` |
| C13 | Provider unavailable |
| C14 | Malformed / contradictory audit linkage |
| C15 | Mixed-corpus aggregation |

---

## 3. Metrics derived

Per case (via `extract_orchestration_run_metrics` / `HandoffMetrics`):

- identity / goal label / status / stop reason / owner action
- step and visit utilisation + limit flags
- handoff counts (allow/deny) and per-handoff policy/lifecycle
- observation snapshot fields (hash, package/truth/pipeline/readiness)
- child ids + optional FR-015 `AgentRunMetrics` roll-up
- optional provider / model / tokens / cost / elapsed (`None` when absent)

C15 aggregate example (acceptance run): 8 fixture runs mixed into one corpus —
handoff totals, deny counts, `provider_unavailable_count=1`, token totals only
where present.

---

## 4. R1–R12 results

| Case | R failures (expected) | Notes |
|------|----------------------|-------|
| C01–C07, C09–C13 | none | Full reconstructability |
| C08 | **R11** | Orphan parent/handoff child ids |
| C12 (×3 fixtures) | none | Stop reasons reconstructable |
| C14 | **R7, R11** | Completed OBS without brief ref + orphan parent child / brief |
| C15 | n/a (aggregate) | Per-member R checked in source fixtures |

Happy-path and deny/stop paths answer R1–R12 from audits alone. Gap cases
**surface** R failures rather than inventing evidence — correct derive-only behaviour.

---

## 5. Correlation / orphan results

| Case | `correlation_complete` | Orphans |
|------|------------------------|---------|
| C01–C07, C09–C13 | true | none |
| C08 | **false** | parent `AGR_ORPHAN`; handoff `AGR_1` |
| C14 | **false** | parent `AGR_1`; brief `OBR_1` not on handoff |
| C12 fixtures | true | deny handoffs without children |

---

## 6. Missing-versus-zero validation

| Case | Result |
|------|--------|
| C06 | `provider`/`model`/tokens/cost all **`None`** |
| C07 | tokens/cost **`0` / `0.0`**; distinct from C06 |
| C09 | join absent → tokens **`None`** (ids still correlate) |
| C15 | missing-only sub-aggregate keeps `total_input_tokens is None` |

Counts remain `0` for empty handoff/event sets. No coercion of missing → zero.

---

## 7. Deterministic repeatability

`run_observability_corpus` runs the suite twice and compares:

- per-case `passed` / `case_id`
- JSON dumps of all `OrchestrationRunMetrics`
- JSON dumps of all `ReconstructabilityReport`s

Acceptance run: **`deterministic_repeat_ok=True`**.

---

## 8. Defects or gaps

| Item | Disposition |
|------|-------------|
| Illegal Pydantic shapes rejected at FR-016 write time | Out of scope — write validators remain FR-016; C14 uses **valid but contradictory** linkage |
| Early `running` with no selection may fail R3 | Documented M1 limitation; not required for M2 corpus terminals |
| Live FR-016 A–T supervisor corpus not re-executed | Intentional — M2 is audit-fixture eval; FR-016 `run_corpus` remains unchanged |
| Metrics CLI | Deferred to optional M3 |
| No defect requiring DOS/BOPA/OBS change | Confirmed |

---

## 9. Product and learning value

| Lens | Assessment |
|------|------------|
| Commercial / job-search effort | Low direct value (eval substrate) |
| Learning / interview transfer | High — derive-only observability, reconstructability as acceptance, missing≠zero |
| Daily prep path | Unchanged — prefer `cic agent run` |
| Horizon 1B | **Unblocked** |

---

## 10. M2 go / no-go

**Verdict: GO**

| Gate | Result |
|------|--------|
| Useful evaluation remains derive-only | **Yes** |
| Reconstructability reliable from existing records | **Yes** |
| Requires runtime instrumentation / new events | **No** → would have been DEFER |
| Requires dashboards / telemetry store | **No** |
| Requires FR-016 redesign | **No** |

**DEFER criteria not met.** Proceed to optional M3 only on owner request; otherwise
FR-017 may pause while Horizon 1B proceeds.

---

## 11. Tests

| Suite | Path | Result |
|-------|------|--------|
| M1 contracts | `tests/unit/multi_agent/test_observability_m1.py` | pass |
| M2 corpus | `tests/unit/multi_agent/test_observability_corpus_m2.py` | pass |

Harness: `run_observability_corpus` / `go_no_go_observability`.

---

## 12. Final repository status

| Item | Status |
|------|--------|
| FR-017 M0 | Accepted |
| FR-017 M1 | Accepted / frozen contracts |
| FR-017 M2 | **Complete — GO** |
| FR-017 M3 | Not started (owner request) |
| FR-017 M4 | Not started |
| Horizon 1B | **Not blocked** |
| DOS / BOPA / OBS / runtime | **Unchanged** |
| ADR-009 | Remains binding |

**Owner next step:** Accept M2 GO unlocked **M3** ([fr017_m3_owner_cli.md](fr017_m3_owner_cli.md)).
Accept M3 to unlock optional M4 — or defer remaining FR-017 and begin Horizon 1B.

Do not implement M4 without explicit owner request.
