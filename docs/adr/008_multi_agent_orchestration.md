# ADR-008: Multi-Agent Orchestration

**Status:** Accepted (FR-016 M1–M4 close-out — **Complete / Frozen**; binding
product posture **GO AS LEARNING PROOF ONLY**)  
**Date:** 2026-08-06  
**Acceptance:** [eval/fr016_multi_agent_orchestration.md](../eval/fr016_multi_agent_orchestration.md)  
**M4:** [eval/fr016_m4_evaluation.md](../eval/fr016_m4_evaluation.md)  
**Reaffirms:** [ADR-003](003_application_workflow_orchestration.md) (orchestration ≠ agent
reasoning; no framework required without failing evidence);
[ADR-005](005_application_pipeline_lifecycle.md) (pipeline advances require owner
authority); [ADR-006](006_recruiter_document_truth_validation.md) (fail-closed truth;
never waive); [ADR-007](007_bounded_agentic_workflow.md) (BOPA frozen; ToolPolicy sole
admission for BOPA actions)  
**Does not amend:** [ADR-001](001_python_yaml_profile_foundation.md),
[ADR-002](002_opportunity_persistence.md),
[ADR-004](004_opportunity_review_boundary.md)

**Spike:** [eval/fr016_m0_engineering_spike.md](../eval/fr016_m0_engineering_spike.md)
(Accepted with revisions)  
**Contracts:** [eval/fr016_m1_orchestration_contracts.md](../eval/fr016_m1_orchestration_contracts.md)  
**Runtime / go-no-go:** [eval/fr016_m2_supervisor_runtime.md](../eval/fr016_m2_supervisor_runtime.md)

---

## Context

FR-015 delivered one bounded agent (BOPA) that coordinates post-acquisition
package/truth readiness under deterministic ToolPolicy. OAT-001 confirmed BOPA is
operationally ready. FR-016 asks whether multiple specialists under a supervisor
add genuine value.

Owner-accepted M0 (with revisions) found:

- Splitting Prep / Truth / Review into separate agents that wrap the same services
  is **multi-agent theatre** and is rejected.
- Near-term commercial value is **modest**; FR-016 is approved primarily as a
  **constrained learning milestone** and as **architectural substrate** for future
  permission-separated capabilities (e.g. Job Discovery).
- The narrow topology is: Deterministic Orchestration Supervisor (DOS) + existing
  BOPA + read-only Operational Briefing Specialist (OBS) + typed handoffs +
  DelegationPolicy + per-specialist ToolPolicy.

---

## Decision

1. **Introduce constrained multi-agent orchestration** under package
   `career_intelligence.multi_agent`. Do **not** place it in FR-008
   `career_intelligence.orchestration`. Do **not** modify
   `career_intelligence.agent` (BOPA) unless a genuine integration defect is
   demonstrated.

2. **Topology (normative):**
   - **DOS** — deterministic supervisor; **delegates only**; performs no domain
     work; gains no specialist authority by sitting above specialists.
   - **BOPA** — existing FR-015 specialist; mutating allow-list **unchanged**.
   - **OBS** — new strictly read-only specialist that produces an
     `OperationalBrief` with cross-surface synthesis BOPA must not absorb by
     broadening `prepare_for_owner_review`.
   - **Typed handoffs** — append-only, policy-validated, idempotent; never
     free-form chat; never grant another specialist’s tools.

3. **Authority model:**
   - **DelegationPolicy** — sole admission authority for specialist invocation.
   - **Per-specialist ToolPolicy** — BOPA keeps `evaluate_action_policy`; OBS has
     `evaluate_obs_action_policy` over a read-only allow-list.
   - Global orchestration limits: max steps, max visits per specialist, repeated
     delegation, circular delegation, no-progress.

4. **Decision policy:** Deterministic supervisor routing and deterministic
   specialist proposers are the **operational default**. Optional LLM may propose
   a specialist or brief wording **only** behind the same deterministic policies.
   LLM output never expands allow-lists.

5. **Explicit theatre rejection:** Do **not** create Application Preparation,
   Truth, or Review “persona” agents that merely rename FR-010/011/014 services or
   BOPA actions. That pattern is multi-agent theatre.

6. **Commercial posture:** Do **not** claim strong near-term commercial value for
   FR-016. Value claims are limited to learning outcomes and future extensibility
   until M2+ evidence shows otherwise.

7. **Mandatory M2 go/no-go review** before M3/M4. At end of M2, evidence must
   answer:
   - Does DOS add value beyond direct `cic agent` / reporting commands?
   - Does OBS remove a meaningful owner task?
   - Do typed handoffs and separated permissions improve safety, auditability, or
     future extensibility?
   - Is the complexity proportionate?
   - Continue to M3/M4, keep as learning proof, or defer until Job Discovery?

8. **Out of scope for FR-016:** job discovery / Seek / LinkedIn / Indeed /
   scraping; automatic submission; pipeline mutation; recruiter contact; truth
   waiver; agent-to-agent free-form conversation; role-play personas; framework
   adoption (LangGraph, OpenAI Agents SDK, Semantic Kernel / MAF, CrewAI) without
   a new ADR and failing product evidence under ADR-003 conditions.

9. **Milestone delivery:**
   - **M1:** contracts + unit tests.
   - **M2:** DOS runtime, handoff store, OBS adapters (read-only), BOPA as child,
     audit — **go/no-go: GO AS LEARNING PROOF ONLY**
     ([eval/fr016_m2_supervisor_runtime.md](../eval/fr016_m2_supervisor_runtime.md)).
   - **M3–M4:** minimal close-out only (not product expansion) on owner request.
     M3 owner CLI complete
     ([eval/fr016_m3_owner_cli.md](../eval/fr016_m3_owner_cli.md));
     **M4 complete** — FR-016 frozen
     ([eval/fr016_m4_evaluation.md](../eval/fr016_m4_evaluation.md);
     [eval/fr016_multi_agent_orchestration.md](../eval/fr016_multi_agent_orchestration.md)).

---

## Alternatives considered

| Alternative | Why rejected / deferred |
|-------------|-------------------------|
| Keep BOPA only (defer FR-016) | Valid commercially; owner accepted constrained learning + substrate path |
| Prep / Truth / Review specialist cast | Multi-agent theatre; no distinct ToolPolicy value |
| LLM coordinator with chat handoffs | Weak deterministic control; injection surface; fashion risk |
| Hierarchical team | Unnecessary complexity for single-user CIC |
| Framework-hosted graph now | ADR-003 conditions unmet; custom contracts portable |
| Broaden BOPA instead of OBS | Would mix brief-only / batch-triage with mutating prepare goal |

---

## Consequences

- FR-016 is **Complete / Frozen / Accepted** as a learning proof
  ([eval/fr016_multi_agent_orchestration.md](../eval/fr016_multi_agent_orchestration.md)).
- Binding product posture remains **GO AS LEARNING PROOF ONLY**; prefer
  `cic agent run` for ordinary preparation.
- BOPA behaviour remains frozen (ADR-007).
- Domain SoTs remain authoritative; orchestration/agent audits are additive.
- Future Acquisition specialist remains a **placeholder** only.
- FR-017 must not begin without explicit owner request.

### Historical note (M1)

At M1 acceptance, contracts were frozen with no runtime until M2. M2–M4 subsequently
delivered runtime, CLI, evaluation, and documentation freeze.

## Guardrails

- DOS must not call mutating domain services directly.
- OBS must never gain `run_preparation`, `verify_package`, `validate_truth_package`,
  submit, pipeline write, or truth-waive tools.
- Handoffs must not widen ToolPolicy.
- Untrusted job/recruiter text must never become orchestration instructions.
- Do not reopen FR-008–FR-016 exit criteria without owner request.
