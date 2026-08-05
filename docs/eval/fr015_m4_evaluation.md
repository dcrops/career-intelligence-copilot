# FR-015 M4 — Evaluation, Observability, and Operational Acceptance

**Date:** 2026-08-05  
**Status:** Complete (M4)  
**Architecture:** [ADR-007](../adr/007_bounded_agentic_workflow.md)  
**Preceding:** [M3 owner CLI](fr015_m3_owner_cli.md)  
**Acceptance:** [fr015_bounded_agentic_workflow.md](fr015_bounded_agentic_workflow.md)  
**Does not begin:** FR-016

---

## 1. Scope

M4 evaluates and closes the existing BOPA. It does **not** add:

- submission authority
- pipeline mutation
- job discovery
- recruiter contact
- truth waiver
- conversational chat
- multi-agent behaviour
- new workflow ownership
- direct persistence or filesystem authority beyond `data/agent_runs/`

Authority boundaries and the M1 allow-list remain unchanged.

---

## 2. Evaluation design

| Layer | Mechanism |
|-------|-----------|
| Corpus | `build_default_corpus` + `run_corpus` against `StaticReadinessBuilder` worlds |
| Proposer comparison | Deterministic vs `AlternatePreferenceProposer` on first snapshots |
| Observability | `extract_run_metrics` / `aggregate_metrics` over AgentRun audit |
| Manual | `scripts/run_fr015_m4_manual.py` (CLI journeys + corpus) |
| Live LLM | Optional (`--llm`); not required for offline acceptance |

Same readiness snapshots drive deterministic and alternate proposals. Policy remains
the sole admission authority. Provider outage and injection fixtures are first-class cases.

---

## 3. Deterministic vs LLM / alternate findings

Offline comparison (16 first-snapshots):

- Deterministic proposals were **always legal** for the primary state.
- Alternate (second legal preference) **disagreed on every case** where a second preference existed — typically preferring `request_owner_review` over prepare/validate/stop.
- Alternate proposals remained **policy-legal**; ToolPolicy would still admit them.
- Disagreement is therefore **preference / sequencing**, not authority expansion.
- Stop-reason consistency under DeterministicActionProposer: **16/16** corpus expectations met.
- Token/cost: null offline (no live provider in acceptance corpus).
- Provider-unavailable: fail-closed (`provider_unavailable`) when proposer raises `AgentProviderError`.

**Operational conclusion:** Deterministic mode remains the default. Explicit `--llm` is optional exploration; it is not required for readiness coordination and was not shown to improve fail-closed outcomes offline.

---

## 4. Observability capability

`career_intelligence.agent.observability` derives from AgentRun audit:

| Signal | Captured |
|--------|----------|
| Run counts | Corpus / aggregate |
| Steps per run | `step_count` |
| Actions proposed / allowed / blocked | Per-run tuples + corpus counts |
| Services executed | Adapter-executed actions |
| Stop reasons | Per-run + histogram |
| Retries | `error_recorded` events |
| Repeated-action prevention | Deny reason containing `repeated no-op` |
| Provider / model | From `ProviderMetadata` when present |
| Token / cost | When provider metadata supplies them |
| Elapsed time | `created_at` → `updated_at` |

Corpus aggregate (acceptance run): 16 runs, 30 steps, mean 1.875 steps; 1 policy block; 1 provider-unavailable.

---

## 5. Corpus results

| Case | Expected stop | Result |
|------|---------------|--------|
| ready_happy_path | completed_for_owner_review | PASS |
| missing_analysis / assessment / strategy | invalid_state | PASS |
| missing_package / cv / cover_letter | completed_for_owner_review | PASS |
| stale_truth | completed_for_owner_review | PASS |
| failing_truth | truth_validation_blocked | PASS |
| package_integrity_failure | completed_for_owner_review | PASS |
| clarification_required | clarification_required | PASS |
| owner_edited_revalidation | completed_for_owner_review | PASS |
| partial_resume | completed_for_owner_review (1 prepare) | PASS |
| contradictory_state | unsupported_state | PASS |
| provider_unavailable | provider_unavailable | PASS |
| policy_blocked_injection | policy_blocked | PASS |

**16/16 PASS**

---

## 6. Owner manual validation

```
python scripts/run_fr015_m4_manual.py
```

**RESULT: PASS** — evidence `data/_fr015_m4_manual/summary.json`

Validated: run, stop, remediation cue, resume, show, history, list, no duplicate prepare, no submit executed, no truth bypass, deterministic default, explicit `--llm` option.

---

## 7. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/agent/test_evaluation.py` | PASS |
| Combined agent unit + FR-015 functional | green (see acceptance) |

---

## 8. Product-value (summary)

See [acceptance report §21](fr015_bounded_agentic_workflow.md). Short form: BOPA removes
post-acquisition prepare→truth sequencing for apply-ready opportunities; does not replace
FR-008 or submission; deterministic default is correct; FR-015 is commercially useful as
a small coordination helper and as substrate for FR-016.

---

## 9. Freeze

FR-015 documentation is frozen via
[fr015_bounded_agentic_workflow.md](fr015_bounded_agentic_workflow.md).
Live Opportunity corpus dogfooding is an **Operational Acceptance Trial** outside
FR-015 exit criteria (acceptance §27).
Do not begin FR-016 without explicit owner request.
