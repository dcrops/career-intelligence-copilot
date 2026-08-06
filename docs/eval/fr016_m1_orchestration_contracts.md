# FR-016 M1 — Multi-Agent Orchestration Contracts

**Date:** 2026-08-06  
**Status:** Complete (M1) — contracts frozen; succeeded by M2 runtime  
**Architecture:** [ADR-008](../adr/008_multi_agent_orchestration.md) (Accepted at M1)  
**Preceding:** [M0 engineering spike](fr016_m0_engineering_spike.md) (Accepted with
revisions)  
**Succeeded by:** [M2 supervisor runtime / go-no-go](fr016_m2_supervisor_runtime.md);
FR-016 later **Complete / Frozen** —
[acceptance](fr016_multi_agent_orchestration.md)  
**Does not begin (historical M1):** M2 runtime was deferred to the next milestone

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Package | `career_intelligence.multi_agent` | Distinct from FR-008 `orchestration` and frozen FR-015 `agent` |
| Topology | DOS + BOPA + OBS | Owner-accepted narrow M0 |
| BOPA | Unchanged; referenced via registry | ADR-007 freeze; no theatre split |
| OBS | Strictly read-only briefing | Distinct ToolPolicy; value BOPA must not absorb |
| Supervisor | Delegation only | No domain super-user |
| Handoffs | Typed, append-only, idempotent | No free-form chat authority |
| Policies | DelegationPolicy + per-specialist ToolPolicy | Privilege escalation fail-closed |
| LLM | Optional propose only (M2+) | Deterministic default |
| M1 deliverable | Contracts + ADR-008 + unit tests | No runtime / CLI / adapters |

```
Owner OrchestrationGoal
  → OrchestrationObservation (derived)
  → BriefingNeedClass / approved specialists
  → SpecialistDelegationProposal (M2+ proposer; M1 data)
  → evaluate_delegation_policy
  → Handoff (append-only)
  → specialist ToolPolicy (OBS or BOPA)
  → (M2+) child run / OperationalBrief
  → orchestration stop reason
```

---

## 2. Why OBS (value beyond BOPA)

OBS exists only where a **read-only briefing delta** would otherwise force
broadening BOPA’s mutating `prepare_for_owner_review` responsibility.

| BriefingNeedClass | Observable signal | Why not BOPA alone |
|-------------------|-------------------|--------------------|
| `pipeline_advises_against_preparation` | Pipeline in submitted / interviewing / offer / terminal | BOPA may still legally prepare on `decision=apply`; owner needs brief-first without mutate tools in-policy |
| `cross_surface_ambiguity` | Contradictory flags or decision holes with artefacts | Diagnose without preparation authority |
| `truth_blockers_need_synthesis` | Owner-facing blocker labels present | Cross-surface brief citing truth + package + prior runs |
| `prior_agent_history_material` | Prior AgentRun ids present | Synthesise history without re-running prep |
| `owner_requested_brief_only` | Goal `brief_opportunity_readiness` / `brief_only` | Mutate must stay impossible under OBS policy |
| `batch_triage` / `post_specialist_synthesis` / `brief_before_mutate` | Reserved for M2+ orchestration modes | Same isolation rationale |
| `no_briefing_delta` | Assessed apply + missing package, no special signals | Prefer direct BOPA; OBS not required |

**Theatre rejection (binding):** Prep Specialist / Truth Specialist / Review
Specialist personas that wrap FR-010/011/014 or BOPA actions are **out of scope**.

---

## 3. Specialist boundaries

### 3.1 DOS (supervisor)

| Owns | Must not |
|------|----------|
| Observe orchestration state | Call mutating domain services |
| Evaluate DelegationPolicy | Bypass specialist ToolPolicy |
| Create/validate typed handoffs | Waive truth / submit / advance pipeline |
| Enforce global budgets / loop controls | Inherit specialist tools |
| Aggregate child stops into orchestration stop | Free-form agent chat |

### 3.2 OBS allow-list

`inspect_readiness`, `inspect_pipeline_context`, `inspect_truth_blockers`,
`inspect_agent_history`, `compose_brief`, `recommend_delegation`,
`request_owner_review`, `stop`.

`recommend_delegation` records a suggestion only — **DelegationPolicy** still
admits any actual specialist invocation.

### 3.3 BOPA allow-list

Unchanged FR-015: `inspect_readiness`, `run_preparation`, `verify_package`,
`validate_truth_package`, `request_owner_review`, `stop`.

Referenced via `BOPA_SPECIALIST` in the registry; not copied as a parallel mutate
surface.

---

## 4. Implementation summary

| API | Role |
|-----|------|
| `OrchestrationGoal` / `OrchestrationRun` / `OrchestrationAuditEvent` | Parent run + append-only audit shapes |
| `OrchestrationObservation` | Derived cross-surface observation |
| `Handoff` | Typed handoff; supervisor-sourced; idempotency key |
| `OperationalBrief` | OBS output (derived) |
| `SpecialistDelegationProposal` / `DelegationDecision` | Delegation proposal + policy result |
| `evaluate_delegation_policy` | Deterministic DelegationPolicy |
| `ObsActionProposal` / `evaluate_obs_action_policy` | OBS ToolPolicy |
| `classify_briefing_needs` / `obs_adds_value_beyond_bopa` | OBS justification helpers |
| `SPECIALIST_REGISTRY` | Static BOPA + OBS contracts |
| `new_orchestration_run_id` / `new_handoff_id` / … | `orr_` / `hof_` / `oae_` / `obr_` ids |

Public surface: `career_intelligence.multi_agent`.

M1 does **not** implement DOS runtime, OBS/BOPA executors, proposers, stores, CLI,
or frameworks.

---

## 5. Validation results

### Unit

`tests/unit/multi_agent/` — **32 passed**.

| Check | Result |
|-------|--------|
| Id patterns / generators | Pass |
| Extra fields forbidden | Pass |
| BOPA allow-list reference unchanged | Pass |
| OBS cannot mutate invariant | Pass |
| Briefing-need classification (OBS value) | Pass |
| DelegationPolicy allow/deny / limits / circular / repeat | Pass |
| Brief goal cannot delegate BOPA | Pass |
| OBS ToolPolicy allow/deny / no-progress | Pass |
| Handoff supervisor-source + accept rules | Pass |
| No privilege escalation via recommend_delegation | Pass |

```
python -m pytest tests/unit/multi_agent/ -q
32 passed
```

---

## 6. Documentation updated

| Document | Change |
|----------|--------|
| ADR-008 | Accepted — DOS + BOPA + OBS; theatre rejected; M2 go/no-go |
| M0 spike | Marked Accepted with revisions |
| Functional specification | FR-016 M1 contracts |
| Domain model | Multi-agent entities |
| ADR index / changelog / roadmap pointers | M1 status |

---

## 7. M2 go/no-go gate (mandatory)

M2 may implement runtime **only** to gather evidence. Before M3:

| Question | Evidence required |
|----------|-------------------|
| Does DOS add value beyond `cic agent` / reporting? | Side-by-side owner journeys |
| Does OBS remove a meaningful owner task? | Interviewing / truth-blocked / history cases |
| Do handoffs + separated permissions improve safety/audit/extensibility? | Illegal delegation / injection / audit replay |
| Is complexity proportionate? | Honest product assessment |
| Continue / learning-proof / defer to Job Discovery? | Explicit owner decision |

---

## 8. Non-goals (M1)

- No production supervisor loop
- No OBS/BOPA adapter execution from DOS
- No CLI namespace
- No framework integration
- No job discovery, submit, pipeline mutation, truth waiver
- No Prep/Truth/Review persona agents
- No changes to frozen BOPA behaviour

---

## 9. M1 acceptance

**M1 contracts + ADR-008 are complete.** Proceed to M2 only on owner request, with
the go/no-go review as a hard gate before M3.
