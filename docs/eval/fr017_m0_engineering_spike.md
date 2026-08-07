# FR-017 M0 — Agent Evaluation & Observability Engineering Spike

**Status:** **Complete (M0 spike)** — **Accepted**; unlocked M1 under narrow scope;
FR-017 later **Complete / Frozen** —
[fr017_agent_evaluation_observability.md](fr017_agent_evaluation_observability.md)  
**Date:** 2026-08-07  
**Phase:** Horizon 1A Stage 11  
**Preceding:** [FR-016 acceptance](fr016_multi_agent_orchestration.md) (Complete /
Frozen / Accepted); [ADR-008](../adr/008_multi_agent_orchestration.md);
[FR-015 acceptance](fr015_bounded_agentic_workflow.md);
[ADR-007](../adr/007_bounded_agentic_workflow.md)  
**Scope (M0):** Document-only architecture spike. **No production code.**  
**Does not begin (M0):** M1 implementation, dashboards, frameworks, Playwright,
FR-016 redesign, Horizon 1B, Masterclass generation.

**Owner direction accepted for this spike:**

1. Preserve the **derive-only** constraint.
2. Strengthen **audit-reconstructability** criteria.
3. **Do not allow FR-017 to block Horizon 1B.**

---

## 1. Executive summary

FR-017 as written in the functional specification is a **laundry list** that largely
duplicates work already frozen in FR-008, FR-014, FR-015, and FR-016.

**Finding:** The only genuine remaining gap is a **thin orchestration-layer
evaluation substrate** — derived metrics over existing `OrchestrationRun` /
`Handoff` / child `AgentRun` audits, plus packaging of offline corpus /
fault-injection patterns already proven in FR-016.

**Finding:** Metrics and reconstructability do **not** require new DOS events,
new SoTs, ToolPolicy changes, or dashboards. Inventory (§4) shows 1:1 mapping from
existing fields.

**Finding:** Horizon 1A **application usability** is already satisfied by
FR-008–FR-015 (with FR-016 optional learning proof). Gating Horizon 1B on FR-017
is process fiction and is **rejected**.

**M0 recommendation:** **GO to M1 under narrow scope** (learning / substrate
posture, derive-only, reconstructability-first). **NO-GO** on the full laundry
list, dashboards, framework observability, and 1B blocking.

---

## 2. Engineering problem (restated)

How do we **evaluate and compare** multi-agent orchestration runs using evidence
**already present** in append-only audits, such that:

1. an owner or engineer can reconstruct the full authority story without guessing;
2. corpus regressions stay offline and deterministic;
3. we do not invent a second system of record or an observability product?

This is **evaluation as derived views**, not instrumentation theatre.

---

## 3. Dual-value and commercial honesty

| Test | Result for narrow FR-017 |
|------|---------------------------|
| Improve interview/offer odds? | Indirect at best |
| Reduce job-search effort? | Marginal (show/history already exist) |
| Required infrastructure? | Modest — eval harness for multi-agent substrate |

**Near-term commercial value: low.**  
**Learning / interview-transferable value: high** if scoped as anti-theatre
evaluation (derive over audits; refuse dashboards).

Daily preparation remains `cic agent run`. FR-017 must not reposition
`cic agent orchestrate` as the default.

---

## 4. Audit inventory (derive-only proof)

### 4.1 Ownership matrix (normative)

| Concern | Owner FR | FR-017 role |
|---------|----------|-------------|
| Workflow traces / checkpoints / retries | FR-008 | None — do not re-instrument |
| Unsupported-claim / truth | FR-014 | None — do not duplicate |
| BOPA metrics / agent corpus | FR-015 M4 (`agent.observability`) | **Reuse** child AgentRun metrics |
| Parent/child audit, handoffs, loop controls | FR-016 | **Source** for derived orchestration metrics |
| Orchestration metrics API + eval packaging | **FR-017 (proposed)** | Derive + aggregate + harness only |
| Dashboards / SaaS observability | — | **Out of scope** |
| Browser / Playwright journeys | Deferred acquisition | **Out of scope** |

### 4.2 OrchestrationRun fields → proposed metrics

| Existing field / structure | Derivable metric / reconstructability signal |
|----------------------------|-----------------------------------------------|
| `orchestration_run_id`, `goal` | Identity; owner goal kind / flags |
| `status`, `stop_reason`, `owner_action_required` | Outcome; owner next step |
| `step_count`, `max_steps` | Step utilisation |
| `max_visits_per_specialist`, `specialist_visits` | Visit counts; visit-limit proximity |
| `handoff_ids` + loaded `Handoff` records | Handoff count; allow/deny; lifecycle |
| `child_agent_run_ids` | Child BOPA refs (join to FR-015 metrics) |
| `last_brief_id` | OBS output ref |
| `last_observation` | Observed state class, package/truth/pipeline, hash |
| `events[]` (`OrchestrationAuditEvent`) | Timeline; selection; policy; specialist start/stop |
| `created_at`, `updated_at` | Elapsed time |
| `checkpoint_ref` | Recovery pointer (not SoT) |
| `owner_approvals_present`, `provider_available` | Gate / availability flags |

### 4.3 Handoff fields → reconstructability

| Field | Reconstructability use |
|-------|------------------------|
| `source` (always `supervisor`) | Proves DOS-sourced delegation |
| `target_specialist`, `requested_goal_kind` | Authority target |
| `reason` | Selection rationale |
| `policy_decision`, `policy_deny_reason` | DelegationPolicy result |
| `acceptance`, `acceptance_reason` | Lifecycle |
| `observed_state_hash`, `idempotency_key` | Idempotency / no-dupe proof |
| `expected_output_kind` | Contracted output |
| `child_agent_run_id` / `child_brief_id` | Specialist result linkage |
| `created_at`, `resolved_at` | Handoff latency (derived) |

### 4.4 Child AgentRun (FR-015 — reuse, do not fork)

When `child_agent_run_ids` is non-empty, call existing
`career_intelligence.agent.observability.extract_run_metrics` — tokens / cost /
provider / action allow-deny already defined. FR-017 must **not** redefine BOPA
metrics.

### 4.5 Derive-only gate (M1 entry criterion)

**Pass condition:** Every M1 metric is expressible as a pure function of stored
`OrchestrationRun` + `Handoff` (+ optional child `AgentRun`) with **zero** new
runtime event kinds and **zero** DOS/BOPA/OBS behaviour changes.

**Fail condition:** Any metric that requires new instrumentation, new SoT, or
policy change → drop the metric or NO-GO that slice.

**M0 result:** Gate **passes** for the narrow metric set in §6.

---

## 5. Strengthened audit-reconstructability criteria

These are **first-class FR-017 acceptance criteria** (stronger than “show elapsed
time”). A frozen FR-017 must prove that from package artefacts + audits alone,
without reading implementation source, an engineer can answer:

| # | Reconstructability question | Evidence source |
|---|----------------------------|-----------------|
| R1 | What owner goal started the run? | `OrchestrationGoal` |
| R2 | What authoritative state was observed (decision, package, truth, pipeline, hash)? | `last_observation` / events |
| R3 | Which specialists were candidates vs selected, and why? | events + handoff `reason` |
| R4 | Did DelegationPolicy allow or deny, and why? | handoff `policy_*` |
| R5 | What ToolPolicy boundary applied to the selected specialist? | specialist registry + presentation/authority (existing); metrics cite specialist id |
| R6 | What was the handoff lifecycle? | `acceptance` trail |
| R7 | What child AgentRun or OperationalBrief resulted? | child ids |
| R8 | Why did orchestration stop? | `stop_reason` |
| R9 | What must the owner do next? | `owner_action_required` |
| R10 | Were global step / visit limits approached or hit? | step/visit fields |
| R11 | Can parent → handoff → child be walked without gaps? | handoff_ids + child refs + events |
| R12 | On resume, was SoT re-inspected (hash change) without duplicate specialist work? | observation hashes + idempotency keys + child completed ops |

**Definition of reconstructability for FR-017:** R1–R12 are demonstrable via
derived metrics + existing `show`/`history` presentation for at least the FR-016
corpus cases A–T (or an explicit subset documented in M1), offline, with no live
LLM required.

Missing R-signals that cannot be derived → either accept as documented limitation
or extend **presentation only** — never by inventing silent domain side effects.

---

## 6. Narrow scope contract (in / out)

### 6.1 In scope for M1+ (if owner accepts GO)

1. `multi_agent.observability` — pure derive of `OrchestrationRunMetrics` /
   corpus aggregates (mirror FR-015 shape, orchestration vocabulary).
2. Join child AgentRun metrics via existing FR-015 helpers when children exist.
3. Package FR-016 corpus + fault-injection cases as an explicit eval API surface
   (thin wrappers / tests — behaviour unchanged).
4. Optional read-only CLI: `cic agent orchestrate metrics <orr_…>` (and/or list
   aggregates) — thin; no dashboard.
5. Documentation: ADR (if needed), M1–M4 eval trail, Academy package after freeze.
6. Reconstructability suite proving R1–R12.

### 6.2 Explicitly out of scope

- Dashboards, chart UIs, SaaS backends (LangSmith-like)
- Framework adoption
- DOS / BOPA / OBS redesign; ToolPolicy / DelegationPolicy changes
- New orchestration audit event kinds (unless M1 proves a genuine gap against R1–R12)
- FR-008 re-instrumentation
- FR-014 claim engine duplication
- Browser / Playwright journey evidence
- Live LLM supervisor evaluation as a core exit criterion
- Making orchestration the daily prep default
- Job Discovery / Horizon 1B features
- Blocking Horizon 1B on FR-017 completion

### 6.3 Laundry-list disposition (functional spec text)

| Spec phrase | Disposition |
|-------------|-------------|
| traces / checkpoints / retries | Already FR-008 — **out** |
| golden workflow tests | Already FR-008 — **out** |
| loop prevention | Already FR-016 — **out** (metrics may *report* limits) |
| unsupported-claim checks | Already FR-014 — **out** |
| token/latency/cost | **Derive** from child AgentRun `ProviderMetadata` when present; null offline OK |
| fault injection / orchestration testing | **In** as harness packaging of existing patterns |
| deterministic replay | **In** as offline static-observation re-run (corpus style) — not live SoT time-travel |
| browser journey evidence | **Out** |
| approval interrupts | Already owner `--approve` — metrics may flag `owner_approvals_present` |

---

## 7. Recommended architecture (M1 sketch — not implementation)

```text
OrchestrationRun + Handoffs (+ child AgentRuns)
        │
        ▼
 multi_agent.observability   ← NEW, read-only, pure functions
        │
        ├── OrchestrationRunMetrics
        ├── corpus aggregate
        └── reconstructability checks (R1–R12)
        │
        ▼
 optional thin CLI / tests / eval scripts
```

**Invariant:** No write path into Opportunity, package, truth, pipeline, or
submission SoTs. No DOS behavioural change.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Observability theatre | Out-of-scope list; M1 ADR/notes forbid dashboards |
| Scope creep into FR-008/014/015 | Ownership matrix §4.1 |
| FR-016 redesign under metrics pressure | Derive-only gate §4.5 |
| Blocking 1B | Normative: **FR-017 must not block Horizon 1B** (§9) |
| Overclaiming commercial value | Learning/substrate posture explicit |
| Reconstructability theatre (checklists without evidence) | R1–R12 must be demonstrated on corpus |

---

## 9. Horizon 1B coupling (normative spike decision)

**Decision:** Horizon 1B (FR-018+) is **not** blocked on FR-017.

**Rationale:**

- Horizon 1 sequencing principle is **job acquisition first**.
- The discover → assess → prepare → review → submit → track loop is already
  delivered by FR-008–FR-015.
- FR-016 is an optional learning proof, not the daily prep path.
- FR-017 (narrow) improves **evaluation substrate**, not application throughput.

**Usable Horizon 1A for unblocking 1B means:** application loop works under owner
approval and truth gates — **not** “every learning FR including eval is frozen.”

Roadmap / functional specification must be amended accordingly (this M0). Owner may
still choose to finish FR-017 before starting 1B for learning continuity; that is
preference, not an engineering gate.

---

## 10. Complexity assessment

| Slice | Effort | Notes |
|-------|--------|-------|
| Derive observability module + tests | Low–medium | Mirror FR-015 |
| Reconstructability assertions on corpus | Low–medium | Strengthen quality bar |
| Thin metrics CLI | Low | Optional in M2/M3 |
| Full laundry list / dashboard | High | Rejected |

---

## 11. Learning value

FR-017 (narrow) teaches:

- evaluation as **derived views over audits**
- reconstructability as an acceptance criterion, not a slide
- continuity with FR-015 observability and FR-016 authority lessons
- why dashboards are not synonymous with observability
- honest low commercial value vs high interview transferability

---

## 12. Academy workflow integration

No process redesign. After FR-017 freeze:

`docs/masterclass/FR017/` via `scripts/build_masterclass_package.py`  
SoT remains `docs/eval/` + ADR. Package is educational packaging only.

---

## 13. Go / no-go

| Option | Decision |
|--------|----------|
| Full functional-spec laundry list | **NO-GO** |
| Dashboard / framework observability | **NO-GO** |
| FR-017 blocks Horizon 1B | **NO-GO** (coupling rejected) |
| Narrow derive-only eval + R1–R12 reconstructability | **GO to M1** |

**Binding posture:** learning / substrate; daily prep unchanged; derive-only;
reconstructability-first; 1B not gated.

---

## 14. Proposed milestones (after owner accepts M0 GO)

| Milestone | Intent |
|-----------|--------|
| **M0** | This spike — **complete** |
| **M1** | Contracts: `OrchestrationRunMetrics`, derive API, R1–R12 check helpers, unit tests; optional ADR-009 if decisions need freezing |
| **M2** | Wire corpus aggregation + reconstructability suite on FR-016 cases; no DOS changes |
| **M3** | Thin owner CLI for metrics (optional if M2 evidence shows CLI unnecessary) |
| **M4** | Evaluation, docs freeze, Academy package |

Do not begin M1 until owner explicitly accepts this M0 GO.

---

## 15. Definition of Done (M0)

| Criterion | Status |
|-----------|--------|
| Inventory of existing audits | Done (§4) |
| Ownership matrix | Done |
| Derive-only gate defined and passed for narrow set | Done |
| Reconstructability criteria R1–R12 | Done (§5) |
| In/out scope contract | Done (§6) |
| Horizon 1B decoupling | Done (§9) |
| Go/no-go | **GO to M1 (narrow)** |
| No production code | Confirmed |

---

## 16. Owner next step

**Done:** Owner accepted M0 GO (narrow scope) and unlocked M1.

**Next:** Accept M1 contracts freeze to unlock M2 (corpus + reconstructability
suite) — **or** defer FR-017 and proceed to Horizon 1B (allowed by §9).

Do not implement M2 without explicit owner request.
