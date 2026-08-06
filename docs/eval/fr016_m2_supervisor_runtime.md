# FR-016 M2 — Deterministic Supervisor Runtime and Go/No-Go Evaluation

**Date:** 2026-08-06  
**Status:** Complete (M2) — **GO AS LEARNING PROOF ONLY** — **historical milestone record**  
**Succeeded by:** [M3](fr016_m3_owner_cli.md); [M4](fr016_m4_evaluation.md);
[acceptance](fr016_multi_agent_orchestration.md)  
**Architecture:** [ADR-008](../adr/008_multi_agent_orchestration.md)  
**Preceding:** [M1 contracts](fr016_m1_orchestration_contracts.md)  
**Did not begin in M2:** M3 CLI productisation, FR-017, job discovery, frameworks

---

## 1. Executive summary

M2 delivered the smallest deterministic multi-agent runtime for the accepted
topology:

**DOS** (delegates only) → **BOPA** (frozen mutating specialist via thin adapter)
and/or **OBS** (strictly read-only operational briefing).

Corpus **A–O: 15/15 PASS**. Manual runner
(`scripts/run_fr016_m2_manual.py`) reconstructs specialist selection, handoffs,
authority, results, stop reasons, and owner actions.

**Go/no-go:** **GO AS LEARNING PROOF ONLY**

- Permission separation, typed handoffs, loop controls, and audit work.
- OBS removes a real owner interpretation task on pipeline-advises and
  truth-blocked cases without broadening BOPA.
- Near-term commercial value remains **modest**: for happy-path prepare,
  direct `cic agent` is still simpler.
- Proceed to a **minimal M3/M4** only to close the learning milestone and
  freeze documentation — **do not claim product value**. Defer richer
  productisation until Job Discovery (or another genuine specialist boundary).

---

## 2. Runtime architecture

```
Owner OrchestrationGoal
        │
        ▼
┌─────────────────────────────────────────────┐
│ DeterministicOrchestrationSupervisor (DOS)  │
│  observe → select → DelegationPolicy        │
│  → typed Handoff → specialist → audit       │
│  → re-observe / stop                        │
│  NO domain service calls                    │
└───────────────┬─────────────────────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
   ObsRuntime        BopaSpecialistAdapter
   (read-only)       → AgentRuntime (FR-015)
        │                │
        ▼                ▼
 OperationalBrief    AgentRun (child)
```

Package: `career_intelligence.multi_agent`  
Persistence: in-memory (tests) / `data/orchestration_runs/` (JSON store)  
BOPA package: **unchanged**.

---

## 3. DOS behaviour

| Step | Behaviour |
|------|-----------|
| Observe | `ObservationBuilder` → `OrchestrationObservation` (+ hash) |
| Select | `select_next_specialist` (deterministic) |
| Delegate | `evaluate_delegation_policy` sole admission |
| Handoff | Append-only lifecycle pending → accepted → executing → completed/stopped |
| Specialist | OBS or BOPA only |
| Stop | Explicit `OrchestrationStopReason`; owner action text when awaiting |
| Forbidden | `attempt_domain_work()` raises `DomainWorkForbiddenError` |

Default limits: max steps 12; max visits/specialist 3; no-progress / repeated /
circular delegation enforced.

---

## 4. BOPA adapter

`BopaSpecialistAdapter` maps:

`Handoff` → `AgentGoal(prepare_for_owner_review)` → `AgentRuntime.start|resume`
→ `BopaSpecialistResult` (child `AgentRun` id + stop reason).

Does **not** change allow-list, ToolPolicy, material-benefit, truth, or owner gates.
DOS cannot impersonate BOPA tools.

---

## 5. OBS behaviour and example briefs

OBS allow-list remains read-only. `ObsRuntime` policy-gates inspect actions then
`compose_brief` → `OperationalBrief`.

**Example — interviewing (pipeline advises):**

- needs: `pipeline_advises_against_preparation`
- next: `owner_review`
- summary: review pipeline before any preparation
- pipeline note: preparation usually unnecessary while interviewing
- **BOPA not selected**

**Example — truth blocked:**

- needs: `truth_blockers_need_synthesis` (+ brief-only if applicable)
- next: `owner_remediate_truth`
- blockers listed; no waive/rewrite

---

## 6. Delegation policy

Unchanged core from M1, used live by DOS:

- brief goals → OBS only
- coordinate + pipeline/ambiguity/truth → OBS first
- coordinate + missing package (no brief-first signals) → BOPA
- `synthesize_after_prepare` → OBS after BOPA once
- visit / step / circular / repeated / approval gates

Owner notes never affect policy inputs (injection-safe).

---

## 7. Handoff lifecycle

Persisted fields include ids, source=`supervisor`, target, opportunity, goal,
state hash, policy result, child AgentRun/brief refs, timestamps, acceptance.

Acceptance values: `pending` → `policy_blocked` | `accepted` → `executing` →
`completed` | `stopped` (also `rejected` / `stale` / `cancelled`).

---

## 8. Orchestration audit / store

`OrchestrationRun` holds goal, status, specialist visits, handoff ids, child
BOPA ids, brief id, budgets, stop reason, owner action, append-only events.

Stores: `InMemoryOrchestrationStore`, `JsonDirectoryOrchestrationStore`
(`data/orchestration_runs/`, `handoffs/`, `briefs/`).

Does **not** replace AgentRun or domain SoTs.

---

## 9. Loop / deadlock controls

| Control | Evidence |
|---------|----------|
| Max global steps | Deny → `orchestration_max_steps` |
| Max visits / specialist | Deny → `specialist_visit_limit` |
| Repeated handoff | Corpus I |
| Circular sequence | Corpus J |
| No-progress | Unchanged observation hash rounds |
| Fail-closed | Provider unavailable → stop (Corpus M) |

---

## 10. Checkpoint / resume

- Full run persisted each step (`checkpoint_ref`).
- `resume` requires `awaiting_owner` or `running`.
- Re-observes authoritative/static state; rejects stale hashes via new observe.
- OBS skips regenerating brief when hash unchanged.
- BOPA adapter resumes incomplete child AgentRun when present.
- Corpus K/L pass.

---

## 11. Corpus results

| ID | Case | Result |
|----|------|--------|
| A | Brief-only | PASS |
| B | Preparation → BOPA → owner stop | PASS |
| C | BOPA → OBS synthesis | PASS |
| D | Pipeline advises → OBS not BOPA | PASS |
| E | Truth-blocked OBS brief | PASS |
| F | Illegal delegation | PASS |
| G | OBS mutate forbidden | PASS |
| H | DOS domain work forbidden | PASS |
| I | Repeated handoff | PASS |
| J | Circular sequence | PASS |
| K | Partial resume / no duplicate prep | PASS |
| L | Stale state re-inspect | PASS |
| M | Provider unavailable | PASS |
| N | Prompt injection | PASS |
| O | Pipeline safety | PASS |

**15/15 PASS** (`career_intelligence.multi_agent.evaluation.run_corpus`).

---

## 12. Manual validation

`python scripts/run_fr016_m2_manual.py` — PASS (journeys 1–7 + corpus).

Owner can see: why specialist selected, authority, handoff, result, stop reason,
next owner action.

---

## 13. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/multi_agent/` (contracts + runtime) | green |
| `tests/unit/agent/test_models.py` + `test_runtime.py` | green (BOPA regression) |
| Corpus A–O | 15/15 |
| Manual runner | PASS |

---

## 14. Value comparison vs direct owner commands

| Scenario | Direct owner | DOS+OBS+BOPA | Verdict |
|----------|--------------|--------------|---------|
| Happy-path prepare | `cic agent run` | DOS→BOPA | Direct is simpler |
| Interviewing + apply + no package | Owner must notice pipeline on `show` | DOS→OBS brief-first | **OBS helps** |
| Truth blockers | `cic agent show` / truth CLI | OBS synthesises blockers | Slight help |
| Illegal submit intent in notes | ToolPolicy on BOPA | Delegation ignores notes | Safety parity |
| Audit across prep+brief | Separate AgentRun + CLIs | Parent OrchestrationRun | **Clearer for learning** |

**Owner commands reduced:** small, mainly for brief-first routing.  
**Non-obvious DOS choices:** yes (D, E, N).  
**OBS removes a meaningful task:** yes for pipeline-advises / truth synthesis
without mutate authority.

---

## 15. Complexity assessment

| Layer | Cost |
|-------|------|
| Contracts + policies | Justified (M1) |
| DOS runtime + stores | Moderate |
| OBS | Small and clear |
| BOPA adapter | Thin |
| Parent/child audit | Useful for FR-017 later |
| Product CLI (M3) | Not yet justified as product |

Complexity is **proportionate as a learning proof**, **not** as a daily
replacement for `cic agent` on happy paths.

---

## 16. Defects and technical debt

| Item | Notes |
|------|-------|
| StaticObservationBuilder queues | Test/corpus convenience; live builder uses readiness |
| Resume after completed brief | Stops with briefing_complete; no re-prep unless state changes |
| No wall-clock timeout yet | Step/visit budgets cover offline; wall clock deferred |
| Presentation is script-only | M3 CLI intentionally not started |
| `synthesize_after_prepare` flag | Explicit opt-in to avoid surprising OBS after every BOPA |

No frozen BOPA behaviour changes. No FR-008–FR-015 reopen.

---

## 17. Mandatory go/no-go recommendation

### Answers to M2 gate questions

| Question | Answer |
|----------|--------|
| Does DOS add value beyond `cic agent` / reporting? | **Yes, narrowly** — non-obvious OBS vs BOPA routing and parent audit. Happy-path prepare: **no**. |
| Does OBS remove a meaningful owner task? | **Yes** — pipeline-advises and truth-blocker synthesis without mutate tools. |
| Do handoffs + separated permissions improve safety/audit/extensibility? | **Yes** — corpus F/G/H/I/J/N/O; clean child AgentRun linkage. |
| Is complexity proportionate? | **For learning/substrate: yes. For near-term product: no.** |
| Continue / learning-proof / defer / reject? | **GO AS LEARNING PROOF ONLY** |

### Binding decision

**2. GO AS LEARNING PROOF ONLY** — complete minimal M3/M4 to close the milestone
and freeze docs; **do not claim product value**. Do not expand specialists.
Revisit product ambition when Job Discovery (or another real permission boundary)
exists.

Not chosen: full GO (overclaims commercial value); NO-GO/DEFER (would abandon
clean learning close-out after a working proof); REJECT (runtime is justified as
proof).

---

## 18. Final repository status

| Item | Status |
|------|--------|
| M0 spike | Accepted with revisions |
| M1 contracts + ADR-008 | Complete |
| M2 DOS + OBS + BOPA adapter | **Complete** |
| Corpus / manual / tests | Green |
| Go/no-go | **GO AS LEARNING PROOF ONLY** |
| M3 | Not started (owner request required; minimal only) |
| FR-017 | Not started |
| BOPA frozen behaviour | Unchanged |

---

## Owner next step

Acknowledge the **GO AS LEARNING PROOF ONLY** decision, then optionally request
minimal M3 (thin owner surface + docs) / M4 freeze — without product marketing
claims.
