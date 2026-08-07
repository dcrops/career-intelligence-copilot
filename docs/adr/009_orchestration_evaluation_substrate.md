# ADR-009: Orchestration Evaluation Substrate (Derive-Only)

**Status:** Accepted (FR-017 M1–M4 close-out — **Complete / Frozen**)  
**Date:** 2026-08-07  
**Acceptance:** [eval/fr017_agent_evaluation_observability.md](../eval/fr017_agent_evaluation_observability.md)  
**M4:** [eval/fr017_m4_evaluation.md](../eval/fr017_m4_evaluation.md)  
**Contracts:** [eval/fr017_m1_observability_contracts.md](../eval/fr017_m1_observability_contracts.md)  
**Spike:** [eval/fr017_m0_engineering_spike.md](../eval/fr017_m0_engineering_spike.md)
(Accepted — narrow GO)  
**Reaffirms:** [ADR-007](007_bounded_agentic_workflow.md) (BOPA metrics ownership);
[ADR-008](008_multi_agent_orchestration.md) (FR-016 audits are learning-proof SoT
for orchestration authority; daily prep remains `cic agent run`);
[ADR-003](003_application_workflow_orchestration.md) (FR-008 owns workflow traces);
[ADR-006](006_recruiter_document_truth_validation.md) (truth engine not duplicated)  
**Does not amend:** ADR-001, ADR-002, ADR-004, ADR-005.

---

## Context

FR-017’s historical laundry list largely duplicated frozen FR-008 / FR-014 /
FR-015 / FR-016 work. M0 rejected dashboards and framework observability and
recommended a **narrow derive-only** evaluation substrate over existing
orchestration audits, with reconstructability R1–R12 as first-class criteria.
Horizon 1B must not be blocked on FR-017.

Owner accepted M0 and authorised M1 contracts only, with an explicit ban on DOS /
BOPA / OBS / Handoff / AgentRun / orchestration runtime changes unless a proven
contract blocker is returned for approval.

---

## Decision

1. **Introduce** `career_intelligence.multi_agent.observability` as a **pure,
   derive-only** module: `OrchestrationRunMetrics`, handoff metrics, corpus
   aggregates, parent/child correlation, and `evaluate_reconstructability`
   (R1–R12).

2. **Reuse** FR-015 `AgentRunMetrics` for child roll-ups. Callers may pass child
   metrics; FR-017 must not redefine BOPA observability or invent a second
   AgentRun metrics schema.

3. **Preserve missing vs zero:** count emptiness as `0`; optional
   provider/model/token/cost/latency absence as `None` — never coerce missing to
   zero.

4. **Do not** add dashboards, telemetry stores, tracing platforms, or new audit
   event kinds. Thin read-only metrics CLI and corpus suite are in scope for M2–M3;
   M4 freezes without broadening.

5. **Do not** modify DOS, BOPA, OBS, Handoff, AgentRun, DelegationPolicy, or
   ToolPolicy unless a genuine R1–R12 contract blocker is proven and owner-approved.

6. **Horizon 1B coupling:** FR-017 must **not** gate FR-018+. Usable application
   loop (FR-008–FR-015) remains the 1B engineering gate.

7. **Product posture:** learning / substrate. Prefer `cic agent run` for ordinary
   preparation; orchestration evaluation does not become the daily default.

8. **Freeze (M4):** FR-017 is Complete / Frozen under
   [eval/fr017_agent_evaluation_observability.md](../eval/fr017_agent_evaluation_observability.md).
   Do not reopen without owner request.

---

## Consequences

- Evaluation becomes **derived views over audits**, consistent with FR-015 M4.
- Reconstructability is testable without live LLM or new instrumentation.
- Scope pressure toward dashboards or runtime instrumentation is rejected by
  this ADR unless owner revisits.
- M2 may package FR-016 corpus cases against these contracts without changing
  specialist behaviour.

---

## Alternatives considered

| Alternative | Disposition |
|-------------|-------------|
| Full laundry-list / dashboard product | Rejected (M0) |
| New DOS event kinds for metrics | Rejected — derive-only gate |
| Fork BOPA metrics inside FR-017 | Rejected — reuse FR-015 |
| Block Horizon 1B on FR-017 | Rejected (M0 §9) |
| Change runtime to satisfy R-signals | Not needed — no blocker in M1 |
