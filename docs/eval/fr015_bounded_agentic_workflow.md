# FR-015 — Bounded Agentic Workflow

**Status:** **Complete** — documentation frozen  
**Date:** 2026-08-05  
**Recommendation:** **FR-015 ACCEPTED**  
**Next:** Begin **FR-016** Multi-Agent Orchestration — **only on explicit owner request**

**ADR:** [ADR-007](../adr/007_bounded_agentic_workflow.md) (Accepted — M1–M4 close-out)

**Milestones:**
[M0](fr015_m0_engineering_spike.md) (Accepted),
[M1](fr015_m1_agent_contracts.md),
[M2](fr015_m2_agent_runtime.md),
[M3](fr015_m3_owner_cli.md),
[M4](fr015_m4_evaluation.md).

---

## 1. Executive Summary

FR-015 delivers the first production **bounded agent** in Career Intelligence Copilot: the
**Bounded Opportunity Preparation Agent (BOPA)**.

| Constraint | Rule |
|------------|------|
| Cardinality | One agent, one Opportunity |
| Timing | Post-acquisition only |
| Authority | Existing CIC services remain authoritative |
| Admission | ToolPolicy is the sole authority for action admission |
| Proposer | Recommends allow-listed actions only |
| Execution | Thin adapters call existing services |
| Forbidden | Submit, pipeline mutation, discovery, recruiter contact, truth waiver, chat, multi-agent, FR-008 repair |
| State | AgentRun status ≠ Opportunity pipeline status |
| Trust | Job-advertisement text is untrusted; never treated as instructions |
| Resume | Idempotent; re-inspects system of record |
| Audit | Append-only under `data/agent_runs/` |

| Milestone | Delivered |
|-----------|-----------|
| M0 | Architecture spike — BOPA; wrapping FR-008 alone is not FR-015 value |
| M1 | Contracts + ADR-007; state classes; ToolPolicy; closed allow-list |
| M2 | AgentRuntime; deterministic + optional OpenAI proposers; thin adapters; checkpoint/resume |
| M3 | Thin `cic agent` CLI (`run` / `resume` / `show` / `history` / `list`) |
| M4 | Corpus evaluation, observability, owner validation, freeze |

**Package:** `career_intelligence.agent`  
**Default proposer:** `DeterministicActionProposer` (`--llm` optional)  
**Active next FR:** **FR-016** (not started — owner request required)

Automated tests, corpus evaluation, and owner manual validation are complete. Repository-wide
dogfooding against the live Opportunity corpus is an **Operational Acceptance Trial**
outside FR-015 exit criteria (see § Dogfooding).

---

## 2. Business Problem

After FR-008–FR-014, the owner still performs repetitive **post-decision readiness
coordination**: decide whether a package exists, whether CV/cover letter are complete,
whether TruthReports are fresh and passing, and which CLI to run next — without granting
the system submission or pipeline authority.

Horizon 1 wins when that coordination reduces effort **without** unsupervised automation.
FR-015 exists so the owner can ask one bounded agent to prepare an Opportunity for owner
review, then stop.

---

## 3. Engineering Problem

How does CIC introduce an agent that:

1. Coordinates existing deterministic capabilities without duplicating them?
2. Remains fail-closed against FR-014 truth, owner review, and package/pipeline policy?
3. Survives prompt injection from job advertisements?
4. Resumes safely without duplicate mutating service calls?
5. Is evaluable offline without requiring live LLM spend for acceptance?

The answer is **not** to wrap FR-008 in an LLM loop, and **not** to give the model
direct tool control. It is policy B: propose → ToolPolicy → services.

---

## 4. Why FR-008 alone was insufficient

FR-008 is the acquisition → analyse → assess → match → strategy → owner-decision runner.
It already provides deterministic sequencing, checkpoints, and bounded LLM retries inside
service-backed nodes ([ADR-003](../adr/003_application_workflow_orchestration.md)).

Wrapping FR-008 as “the agent” would:

- Add no genuine agency beyond deterministic routing already present
- Blur orchestration with agent reasoning
- Tempt re-entry into frozen FR-008 exit criteria for prep/truth work owned elsewhere

BOPA’s value is **post-acquisition readiness coordination** (package / truth /
diagnose-and-stop) on concrete readiness state classes — documented in M0/M1 — not
re-running the acquisition workflow.

---

## 5. BOPA architecture

```
Owner: cic agent run <opportunity_id> --approve
              │
              ▼
     ReadinessSnapshot (derived observation)
              │
              ▼
     ReadinessStateClass (priority classification)
              │
              ▼
     ActionProposer  ──suggests──►  AgentActionProposal
              │
              ▼
     ToolPolicy (evaluate_action_policy)  ──allow / deny──
              │
        allow │
              ▼
     Thin adapter → existing CIC service
              │
              ▼
     AgentRun audit event (append-only)
              │
              ▼
     Stop (owner action required) or continue
```

**Does not own:** FR-002–005 workflow execution, submission, pipeline advances,
discovery, Markdown rewrite, truth waiver.

**May request (allow-list only):** `inspect_readiness`, `run_preparation`,
`verify_package`, `validate_truth_package`, `request_owner_review`, `stop`.

---

## 6. ADR-007 summary

[ADR-007](../adr/007_bounded_agentic_workflow.md) freezes:

1. BOPA as the sole FR-015 agent (`prepare_for_owner_review`)
2. Do not wrap or extend FR-008 as the agent
3. Decision policy B normative (proposer suggests; ToolPolicy admits)
4. Closed allow-list; forbidden actions enumerated
5. Concrete readiness state classes first-class
6. Fail closed on truth / invalid / contradictory / approvals / provider / max steps / no-ops
7. AgentRun audit additive — not a second Opportunity SoT
8. Milestone delivery M1–M4 frozen; deterministic proposer operational default
9. Multi-agent deferred to FR-016; orchestration-layer eval to FR-017

---

## 7. Runtime architecture

`AgentRuntime` loop (M2): observe → propose → ToolPolicy → execute thin adapter →
audit → stop/continue.

| Component | Role |
|-----------|------|
| `LiveReadinessBuilder` / `StaticReadinessBuilder` | Derive ReadinessSnapshot |
| `DeterministicActionProposer` / `OpenAIActionProposer` | Suggest next action from typed readiness fields only |
| `evaluate_action_policy` | Sole admission authority |
| `ServiceActionExecutor` / `ScriptedActionExecutor` | Thin service calls; idempotent skips |
| `JsonDirectoryAgentRunStore` | `data/agent_runs/` persistence |
| `build_agent_runtime` | CLI factory |

Immediate-stop state classes short-circuit mutating coordination (e.g. missing
FR-002–005 → `invalid_state`; truth fail → `truth_validation_blocked`; ready →
`completed_for_owner_review`).

---

## 8. State-class model

`ReadinessStateClass` values (priority order) classify where BOPA adds value beyond
FR-008. Each class defines approved actions and expected owner-stop reasons
([M1](fr015_m1_agent_contracts.md)).

Representative classes: missing analysis/assessment/strategy (diagnose/stop);
missing/incomplete/stale package or integrity failure (prepare/verify path);
missing/stale/failing truth or owner-edited Markdown (revalidate / block);
clarification; provider unavailable; contradictory; partial resume; ready for owner
review.

Missing upstream FR-002–005 artefacts are **diagnosed and stopped** — never repaired
by re-entering FR-008 from the agent.

---

## 9. ToolPolicy

`evaluate_action_policy` is the only path from proposal to execution.

- Allow only if action ∈ approved set for primary state
- Deny hard-forbidden / out-of-enum / repeated no-op on unchanged snapshot / max steps
- Deny does not expand authority; injection cannot grant submit or truth waive
- Detection of illegal proposals yields `policy_blocked` (or mapped stop reason)

---

## 10. Proposer model

| Proposer | Role |
|----------|------|
| `DeterministicActionProposer` | **Operational default** — preferred legal action per state |
| `OpenAIActionProposer` | Optional (`--llm`) — structured proposal from readiness flags only; never job-ad body as instructions |
| `AlternatePreferenceProposer` | Offline evaluation stand-in for disagreement measurement |

Proposer recommends; ToolPolicy authorises. Provider outage → fail-closed
`provider_unavailable`.

---

## 11. Adapter model

Thin adapters map allow-listed actions to existing services (preparation, package
verify, truth validate). They:

- Do not invent business rules
- Support idempotent skip when the operation is already satisfied
- Do not grant filesystem/shell/direct persistence beyond service APIs and agent-run store
- Do not submit or advance pipeline

---

## 12. Audit model

`AgentRun` + append-only `AgentAuditEvent` records:

- Snapshot observed, action proposed, policy evaluated, action executed/blocked
- Service results / refs, errors, stop recorded, resume observed

Audit is recovery and explainability data — not Opportunity, package, truth,
submission, or pipeline SoT.

---

## 13. Checkpoint / Resume

- Runs checkpoint under `data/agent_runs/`
- `cic agent resume <id> --approve` clears awaiting status and continues
- Resume **re-inspects** system of record (`inspect_readiness` first)
- Completed preparation/truth operations are not duplicated when already satisfied
- Agent status remains independent of Opportunity pipeline status

---

## 14. Prompt-injection protection

- Job-advertisement / JD text is **untrusted data**, never agent instructions
- Proposers receive typed readiness fields only
- ToolPolicy denies actions illegal for the primary state regardless of rationale text
- Corpus fixture: injection-style rationale proposing illegal-for-state
  `validate_truth_package` → `policy_blocked`; no execute

---

## 15. Failure semantics

| Condition | Stop / behaviour |
|-----------|------------------|
| Missing FR-002–005 | `invalid_state` |
| Truth FAIL / blocked | `truth_validation_blocked` |
| Clarification needed | `clarification_required` |
| Contradictory / unsupported | `unsupported_state` |
| Owner approvals missing (prep path) | `owner_approval_required` |
| Policy deny | `policy_blocked` (or mapped) |
| Provider outage | `provider_unavailable` |
| Max steps / unexpected | `max_steps_reached` / `unexpected_failure` |
| Ready | `completed_for_owner_review` |

Never coerce to unsafe success. Never waive truth. Never silent submit.

---

## 16. Owner workflow

```
cic agent run <opportunity_id> --approve
  → readiness → (prepare / truth as policy allows) → stop
  → report: readiness, steps, policy, executed, stop, owner action

# after truth remediation / owner Markdown edit:
cic truth validate-package …
cic agent resume <agent_run_id> --approve

cic agent show <agent_run_id>
cic agent history <agent_run_id>
cic agent list
```

`--approve` required for run/resume. Deterministic proposer default; `--llm` optional.

---

## 17. Observability

M4 (`observability.py`): run counts; steps; actions proposed/allowed/blocked; services
executed; stop reasons; retries; repeated-action blocks; provider/model; tokens/cost
when available; elapsed time. Aggregation via `aggregate_metrics`.

Acceptance corpus: **16 runs**, **30 steps**, mean **1.875**; **1** policy block;
**1** provider-unavailable.

Bounded-agent observability is in scope for FR-015 M4. Orchestration-layer evaluation
remains **FR-017**.

---

## 18. Corpus evaluation summary

Harness: `career_intelligence.agent.evaluation` — **16/16 PASS**
([M4](fr015_m4_evaluation.md)).

Covers: ready path; missing FR-002–005; missing package/CV/CL; stale/failing truth;
integrity failure; clarification; owner-edited revalidation; partial resume (single
prepare); contradictory; provider unavailable; policy-blocked injection.

Deterministic vs alternate: deterministic always legal; alternate often disagrees on
sequencing while remaining policy-legal — preference, not authority expansion.

---

## 19. Manual validation summary

| Script | Result |
|--------|--------|
| `scripts/run_fr015_m2_manual.py` | PASS |
| `scripts/run_fr015_m3_manual.py` | PASS |
| `scripts/run_fr015_m4_manual.py` | PASS (`data/_fr015_m4_manual/summary.json`) |

M4 validated: run, stop, remediation cue, resume, show, history, list, no duplicate
prepare, no submit executed, no truth bypass, deterministic default, explicit `--llm`.

---

## 20. Test summary

| Suite | Scope |
|-------|-------|
| `tests/unit/agent/` | Contracts, policy, runtime, CLI presentation, evaluation/observability |
| `tests/functional/test_fr015_m2_*.py` | Runtime functional |
| `tests/functional/test_fr015_m3_*.py` | Owner CLI functional |

Agent-related suites green at freeze (**67** unit agent + FR-015 functional).

---

## 21. Product-value assessment

**Removes for the owner (apply-path, artefacts present):** manual “what next?” across
package/truth; hand-sequencing preparation then truth validate; resume without
re-preparing.

**Value over FR-008:** post-acquisition readiness coordination FR-008 does not own.

**Does not add:** discovery; repairing missing analysis; submission; pipeline;
recruiter outreach; chat; multi-agent.

**LLM proposer:** not shown to improve fail-closed outcomes offline. Deterministic
default remains correct.

**Commercial posture:** small real coordination helper **and** substrate for FR-016 —
not a substitute for multi-agent product ambition.

---

## 22. Technical debt classification

| Item | Class | Justification |
|------|-------|---------------|
| Live LLM cost/latency golden samples | **Deferred → FR-017** | Optional; not required for BOPA operational default |
| Clarification overlay on LiveReadinessBuilder (kwargs) | **Accepted** | Live path sufficient; Static preserves fixtures; no product defect at freeze |
| Bounded-agent vs orchestration observability split | **Accepted** | M4 covers BOPA; FR-017 owns multi-agent eval |
| `AlternatePreferenceProposer` offline stand-in | **Accepted** | Eval-only; not a production proposer |
| Agent repairs missing FR-002–005 via FR-008 re-entry | **Out of Scope** | Explicit non-goal; diagnose/stop only |
| Submit / pipeline / discovery / truth-waive tools | **Out of Scope** | Require new ADR + owner acceptance |
| Multi-agent messaging / handoffs | **Future FR (FR-016)** | Explicitly deferred |
| Repository-wide live Opportunity dogfooding | **Deferred (OAT)** | Outside FR-015 acceptance; see § Dogfooding |

---

## 23. Risks considered

| Risk | Mitigation |
|------|------------|
| Agent becomes second workflow engine | Do not wrap FR-008; diagnose/stop on missing artefacts |
| LLM bypasses truth or submit | Closed allow-list; ToolPolicy; no submit/waive tools |
| Prompt injection from JD | Typed readiness only; policy deny; corpus fixture |
| Duplicate mutating ops on resume | Idempotent adapters; re-inspect; completed-op records |
| Agent status confuses pipeline | Explicit presentation; separate AgentRun store |
| Premature multi-agent | FR-016 gated on owner request |

---

## 24. Engineering retrospective

**What worked well**

- Policy B kept authority crisp and testable
- State-class matrix made “value beyond FR-008” concrete
- Deterministic default enabled offline acceptance without API spend
- Resume + idempotent adapters prevented duplicate preparation

**Why a bounded agent**

- Genuine next-action selection under policy after acquisition, without unsupervised automation

**Why FR-008 remained separate**

- Orchestration ≠ agent reasoning ([ADR-003](../adr/003_application_workflow_orchestration.md));
  reopening FR-008 for prep/truth would blur frozen boundaries

**Why Policy B**

- Direct LLM-to-tools is unsafe and weakly testable; deterministic admission is the control plane

**Why deterministic remained the default**

- Clearer prepare→validate→stop sequencing; cheaper; offline-evaluable; LLM optional under same policy

**Lessons**

- Document concrete state classes before runtime
- Evaluation fixtures must preserve readiness markers (Static builder)
- Authority non-goals must be enumerated early and frozen in ADR

**Guidance for FR-016**

- Do not begin without owner request
- Preserve ToolPolicy / allow-list discipline per specialist
- Do not collapse agent status into pipeline status
- Do not weaken FR-014
- Prefer genuine engineering boundaries over role-play agents
- Keep deterministic fallbacks where sequencing is already known

---

## 25. Operational readiness

| Gate | Status |
|------|--------|
| Architecture accepted | Met |
| Contracts / runtime / policy / adapters | Met |
| Audit / checkpoint / CLI | Met |
| Evaluation / manual / tests | Met |
| Docs frozen | Met |
| Production CLI surface | `cic agent` ready for owner use |
| Live corpus dogfooding | **Not** an FR-015 exit gate — see OAT below |

---

## 26. Production operational workflow

Documented production path after FR-015 (apply-path; owner judgment retained):

```
Job Analysis (FR-002)
      ↓
Opportunity Assessment (FR-003)
      ↓
Portfolio Match (FR-004)
      ↓
Application Strategy (FR-005)
      ↓
CV Generation (FR-006)
      ↓
Cover Letter Generation (FR-007)
      ↓
Application Package (FR-010 / FR-011)
      ↓
Truth Validation (FR-014)
      ↓
Bounded Opportunity Preparation Agent (FR-015)
      ↓
Owner Review (mandatory)
      ↓
Submission (FR-012 — never silent)
      ↓
Pipeline Tracking (FR-013)
```

**Notes (architecture fidelity):**

- FR-008 acquisition/orchestration precedes this slice; FR-009 persistence/review may
  record apply before package work.
- BOPA coordinates readiness: it may invoke preparation and truth validation when
  policy allows, then **stops for owner review**. It does not submit or advance pipeline.
- Truth Validation remains fail-closed; BOPA consumes gates and never waives them.
- AgentRun is independent of Opportunity pipeline status.

---

## 27. Dogfooding — Operational Acceptance Trial (outside FR-015)

Repository-wide operational testing against the **real Opportunity corpus** is
intentionally **outside FR-015 acceptance**. Treat it as a separate **Operational
Acceptance Trial (OAT)** after documentation freeze.

**Expected OAT plan (documentation only — no implementation in this task):**

1. Select a representative sample of live Opportunities (apply-ready, missing package,
   truth-blocked, incomplete artefacts).
2. Run `cic agent run … --approve` with the deterministic default; record stop reasons.
3. Perform owner remediation (truth / Markdown / package) where stopped; resume once.
4. Confirm: no duplicate preparation; no pipeline mutation; no truth bypass; agent
   status ≠ pipeline status.
5. Optionally spot-check `--llm` under the same ToolPolicy (non-blocking).
6. Capture findings in an OAT note under `docs/eval/` if the owner elects to record them —
   without reopening FR-015 exit criteria unless a defect requires it.

OAT success is operational confidence for day-to-day use; it is not a prerequisite to
mark FR-015 complete.

---

## 28. Definition of Done

| Criterion | Status |
|-----------|--------|
| Architecture accepted (M0 + ADR-007) | **Met** |
| Contracts complete (M1) | **Met** |
| Runtime complete (M2) | **Met** |
| Policy complete | **Met** |
| Adapters complete | **Met** |
| Audit / checkpointing complete | **Met** |
| CLI complete (M3) | **Met** |
| Evaluation complete (M4) | **Met** |
| Manual validation complete | **Met** |
| Tests green | **Met** |
| Docs frozen | **Met** |
| FR-016 not started | **Met** |

---

## 29. Final acceptance recommendation

**Accept and freeze FR-015.**

Proceed to **FR-016 Multi-Agent Orchestration** only on explicit owner request.
Do not reopen FR-015 exit criteria without owner request. Keep FR-014 fail-closed
gates in force for any future automation increase.

---

## 30. Final repository status

| Item | Status |
|------|--------|
| FR-001–FR-014 | Complete and frozen (unchanged) |
| FR-015 Bounded Agentic Workflow | **Complete and frozen** |
| FR-016 Multi-Agent Orchestration | **Active FR — not started** (owner request required) |
| Package | `career_intelligence.agent` |
| CLI | `cic agent` |
| Store | `data/agent_runs/` |
| ADR | [ADR-007](../adr/007_bounded_agentic_workflow.md) (Accepted) |
| Milestones | M0–M4 complete — see header links |
| OAT (live corpus) | Separate trial — outside FR-015 exit criteria |

Authority preserved: no submission, pipeline mutation, discovery, recruiter contact,
truth waiver, conversational chat, multi-agent behaviour, new workflow ownership, or
direct filesystem authority beyond agent-run audit storage.
