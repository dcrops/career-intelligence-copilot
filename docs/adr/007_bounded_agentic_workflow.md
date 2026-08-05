# ADR-007: Bounded Agentic Workflow

**Status:** Accepted (FR-015 complete — M1–M4 frozen)  
**Date:** 2026-08-05  
**Reaffirms:** [ADR-003](003_application_workflow_orchestration.md) (thin FR-008 runner;
orchestration ≠ agent reasoning); [ADR-006](006_recruiter_document_truth_validation.md)
(fail-closed truth; agent may consume, never waive); [ADR-005](005_application_pipeline_lifecycle.md)
(pipeline advances require owner authority)  
**Does not amend:** [ADR-001](001_python_yaml_profile_foundation.md),
[ADR-002](002_opportunity_persistence.md),
[ADR-004](004_opportunity_review_boundary.md)

**Spike:** [eval/fr015_m0_engineering_spike.md](../eval/fr015_m0_engineering_spike.md)
(Accepted with clarification)  
**Contracts:** [eval/fr015_m1_agent_contracts.md](../eval/fr015_m1_agent_contracts.md)  
**Runtime / CLI / eval:** [M2](../eval/fr015_m2_agent_runtime.md),
[M3](../eval/fr015_m3_owner_cli.md), [M4](../eval/fr015_m4_evaluation.md)  
**Acceptance:** [eval/fr015_bounded_agentic_workflow.md](../eval/fr015_bounded_agentic_workflow.md)

---

## Context

FR-008 already provides deterministic workflow orchestration (acquire → analyse →
assess → match → strategy → persist → owner review → record decision) with
checkpoints and bounded LLM retries inside service-backed nodes. FR-011–FR-014
add preparation, submission, pipeline, and truth gates **outside** that runner.

Horizon 1A Stage 9 requires a **first bounded agent** that coordinates existing
capabilities without becoming a second workflow engine, without silent submit,
and without weakening FR-014.

Owner-accepted M0 architecture (clarified at M1): **Bounded Opportunity
Preparation Agent (BOPA)** — one agent, one Opportunity, post-acquisition only;
LLM proposes an allow-listed action; deterministic ToolPolicy validates; existing
CIC services execute.

---

## Decision

1. **Introduce BOPA as the sole FR-015 agent.** Package:
   `career_intelligence.agent`. Goal kind M1: `prepare_for_owner_review`.

2. **Do not wrap or extend FR-008 as the agent.** `ApplicationWorkflowRunner`
   remains the acquisition/pre-decision workflow engine. BOPA starts from a
   persisted `opportunity_id` and coordinates **post-acquisition readiness**
   (package / truth / owner-stop diagnosis). Missing FR-002–FR-005 artefacts are
   **diagnosed and stopped** — not repaired by re-entering the FR-008 graph from
   the agent in M1.

3. **Decision policy B is normative.** ActionProposer (M2+) may suggest
   `AgentAction` values; `evaluate_action_policy` is the sole authority for
   admission. Direct LLM-to-tools is rejected.

4. **M1 allow-list is closed.** Allowed actions:
   `inspect_readiness`, `run_preparation`, `verify_package`,
   `validate_truth_package`, `request_owner_review`, `stop`.
   Forbidden (not in enum; documented in `FORBIDDEN_ACTION_NAMES`): submit,
   pipeline mutation, discovery, recruiter contact, truth waive, Markdown rewrite,
   opportunity decision mutation, analyse/assess/match/strategy tools, filesystem,
   shell, arbitrary code.

5. **Concrete readiness state classes are first-class.** Snapshots classify into
   `ReadinessStateClass` values that define approved actions, blocked actions,
   owner-stop reasons, and audit expectations. BOPA’s value beyond FR-008 is
   defined per class in the M1 contracts record — not assumed.

6. **Fail closed.** Truth FAIL / stale / review_required, missing upstream
   artefacts, contradictory state, missing owner approvals, provider outage,
   max steps, and repeated no-ops yield deny or explicit `AgentStopReason`.
   Never coerce to unsafe success.

7. **AgentRun audit is additive.** Append-only events under a future
   `data/agent_runs/` store (M2+) do not replace Opportunity, workflow,
   package, truth, submission, or pipeline records.

8. **Milestone delivery (frozen).** M1 contracts; M2 AgentRuntime + proposers +
   thin adapters + `data/agent_runs/` audit; M3 `cic agent` CLI; M4 corpus
   evaluation + observability + operational acceptance. Deterministic proposer is
   the operational default; `--llm` is optional under the same ToolPolicy.

9. **Out of scope for FR-015.** Multi-agent orchestration (FR-016), orchestration-layer
   evaluation (FR-017 — M4 covers bounded-agent observability only), job-board access,
   autonomous submit, chatbot UX as primary interface.

---

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Wrap FR-008 runner only | No genuine agency; duplicates deterministic routing |
| Expand FR-008 graph with prep/truth nodes | Reopens frozen FR; blurs orchestration and agency |
| Fully deterministic macro as FR-015 | Valid product helper; does not meet FR-015 agentic purpose |
| LLM direct tool control | Unsafe; weak testability; injection surface |
| Agent repairs missing analysis via tools | Re-enters FR-008 responsibilities — diagnose/stop |

---

## Consequences

- FR-015 is **complete and frozen**. Do not reopen exit criteria without owner request.
- FR-014 / FR-013 / FR-012 boundaries remain consumed, not reinterpreted.
- DeterministicActionProposer remains the operational default (M4 finding).
- LangGraph / external agent frameworks remain out unless a future ADR presents
  failing product evidence (consistent with ADR-003).
- FR-016 must not begin without explicit owner request.

## Guardrails

- Do not add submit, pipeline write, discovery, or truth-waive tools without a new
  ADR and explicit owner acceptance.
- Do not treat job-advertisement text as agent instructions.
- Do not silently set FR-006/007 approval flags.
- Do not implement agent-to-agent messaging in FR-015 (deferred to FR-016).
