# FR-015 M1 — Bounded Agent Contracts

**Date:** 2026-08-05  
**Status:** Complete (M1) — contracts frozen  
**Architecture:** [ADR-007](../adr/007_bounded_agentic_workflow.md) (Accepted)  
**Preceding:** [M0 engineering spike](fr015_m0_engineering_spike.md) (Accepted with
clarification)  
**Succeeded by:** [M2](fr015_m2_agent_runtime.md) → [acceptance](fr015_bounded_agentic_workflow.md)  
**Does not begin:** FR-016

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Package | `career_intelligence.agent` | Distinct from FR-008 `orchestration` |
| Agent | BOPA only | Owner-accepted M0 |
| Policy | LLM propose (M2+) + deterministic ToolPolicy (M1) | Safety + genuine agency |
| Start | Persisted `opportunity_id`, post-acquisition | No discovery / no FR-008 wrap |
| Missing FR-002–005 | Diagnose + owner-stop | Do not re-enter FR-008 from agent in M1 |
| M1 deliverable | Contracts + ADR-007 + unit tests | No runtime / CLI / provider |

```
Owner goal (prepare_for_owner_review)
  → ReadinessSnapshot (derived)
  → ReadinessStateClass (priority classify)
  → AgentActionProposal (M2+ provider; M1 tested as data)
  → ToolPolicy.evaluate_action_policy
  → (M2+) thin adapter → existing CIC service
  → append AgentAuditEvent
  → stop at AgentStopReason
```

---

## 2. Value beyond FR-008 — concrete state classes

FR-008 owns the linear pre-decision graph. BOPA adds value on **cross-surface
readiness** after an Opportunity exists — especially package/truth recovery and
fail-closed diagnosis when upstream artefacts or approvals are wrong.

For each class below:

1. **Observable condition** — fields on `ReadinessSnapshot`
2. **Approved next actions** — subset of M1 allow-list
3. **Blocked actions** — illegal even if a model proposes them
4. **Owner-stop condition** — when the agent must stop rather than coordinate
5. **Expected audit record** — minimum `AgentAuditEvent` / step evidence

### 2.1 `missing_analysis`

| Field | Definition |
|-------|------------|
| Observable | `artefacts.job_analysis == false` |
| Approved | `inspect_readiness`, `request_owner_review`, `stop` |
| Blocked | `run_preparation`, `verify_package`, `validate_truth_package`; all analyse tools (not in allow-list) |
| Owner-stop | Yes — `invalid_state` (complete analysis via existing FR-008/services, not BOPA) |
| Audit | `snapshot_observed` with state_class; `policy_evaluated` deny on prep; `stop_recorded` |

**Beyond FR-008:** Explains a durable Opportunity with a hole FR-008’s happy path
would not leave; does not invent analysis.

### 2.2 `missing_assessment`

| Field | Definition |
|-------|------------|
| Observable | `artefacts.assessment == false` |
| Approved | `inspect_readiness`, `request_owner_review`, `stop` |
| Blocked | prep / verify / validate; assess tools |
| Owner-stop | Yes — `invalid_state` |
| Audit | Same pattern as 2.1 |

### 2.3 `missing_portfolio_match` / `missing_strategy`

| Field | Definition |
|-------|------------|
| Observable | `artefacts.portfolio_match == false` or `artefacts.strategy == false` |
| Approved | `inspect_readiness`, `request_owner_review`, `stop` |
| Blocked | prep / verify / validate; match/strategy tools |
| Owner-stop | Yes — `invalid_state` |
| Audit | Same pattern as 2.1 |

### 2.4 `missing_package` / `stale_package`

| Field | Definition |
|-------|------------|
| Observable | `decision == apply`, artefacts complete, `package.status` in `{absent, stale}` |
| Approved | `inspect_readiness`, `run_preparation` (**if** `owner_approvals_present`), `request_owner_review`, `stop` |
| Blocked | `validate_truth_package` while absent; submit/pipeline; prep without approvals |
| Owner-stop | If approvals missing → `owner_approval_required`; else may coordinate prep |
| Audit | `action_proposed` / `policy_evaluated` / future `service_result` citing preparation run id |

**Beyond FR-008:** FR-008 does not own package composition; this is core BOPA value.

### 2.5 `missing_cv` / `missing_cover_letter`

| Field | Definition |
|-------|------------|
| Observable | `package.status == incomplete` and the corresponding draft flag is false |
| Approved | Same as missing/stale package (prep when approvals present) |
| Blocked | `validate_truth_package`; claiming `ready_for_owner_review` |
| Owner-stop | Approvals missing → `owner_approval_required` |
| Audit | State class distinguishes which draft is missing |

### 2.6 `package_integrity_failure`

| Field | Definition |
|-------|------------|
| Observable | `package.status == integrity_failed` with `manifest_ref` |
| Approved | `inspect_readiness`, `verify_package`, `run_preparation` (with approvals), `request_owner_review`, `stop` |
| Blocked | `validate_truth_package` until integrity restored; submit |
| Owner-stop | Optional after verify confirms failure and owner must repair paths |
| Audit | `verify_package` result summary; deny validate with reason |

### 2.7 `missing_truth_report` / `stale_truth_report`

| Field | Definition |
|-------|------------|
| Observable | Package present (or stale with drafts); truth `absent` or `stale` |
| Approved | `inspect_readiness`, `validate_truth_package`, `request_owner_review`, `stop` |
| Blocked | Treating prior PASS as current; waive findings; submit |
| Owner-stop | After validate yields fail/review_required → transitions to `truth_blocked` |
| Audit | Truth report ref; policy allow on validate; outcome on future service_result |

**Beyond FR-008:** Truth is FR-014; BOPA coordinates revalidation.

### 2.8 `owner_markdown_revalidation_required`

| Field | Definition |
|-------|------------|
| Observable | `truth.owner_edited_markdown_since_validation == true` (status cannot remain `pass`) |
| Approved | `inspect_readiness`, `validate_truth_package`, `request_owner_review`, `stop` |
| Blocked | Rewrite Markdown; claim completed_for_owner_review on stale PASS |
| Owner-stop | If revalidation fails → `truth_validation_blocked` |
| Audit | Flag + prior report ref; revalidation event |

### 2.9 `truth_blocked`

| Field | Definition |
|-------|------------|
| Observable | `truth.status` in `{fail, review_required}` |
| Approved | `inspect_readiness`, `validate_truth_package`, `request_owner_review`, `stop` |
| Blocked | Waive; rewrite; submit; pipeline advance |
| Owner-stop | Yes — `truth_validation_blocked` |
| Audit | Blocking finding codes; stop reason; no mutation of Markdown |

### 2.10 `clarification_required`

| Field | Definition |
|-------|------------|
| Observable | `clarification_required == true` with message |
| Approved | `inspect_readiness`, `request_owner_review`, `stop` |
| Blocked | All mutating actions (`run_preparation`, validate-as-progress) |
| Owner-stop | Yes — `clarification_required` |
| Audit | Clarification message preserved on snapshot_observed / stop_recorded |

### 2.11 `partial_agent_run`

| Field | Definition |
|-------|------------|
| Observable | `prior_agent_run_incomplete == true` with `prior_agent_run_id` |
| Approved | `inspect_readiness`, `request_owner_review`, `stop` (then reclassify on fresh snapshot) |
| Blocked | Blind replay of prior mutating actions without refreshed snapshot |
| Owner-stop | Only if refreshed snapshot demands it |
| Audit | `resume_observed` citing prior run id; new snapshot hash |

**Beyond FR-008:** Agent-run checkpoints are distinct from `data/workflow_runs/`.

### 2.12 `provider_unavailable`

| Field | Definition |
|-------|------------|
| Observable | `provider_available == false` |
| Approved | `inspect_readiness`, `stop` |
| Blocked | Any action that would require accepting a model proposal to mutate (prep/validate) |
| Owner-stop | Yes — `provider_unavailable` (after readiness report) |
| Audit | Provider metadata absent/error; stop reason; readiness still recorded |

### 2.13 `unsupported_or_contradictory`

| Field | Definition |
|-------|------------|
| Observable | `contradictory_flags` non-empty; **or** `decision != apply` for this goal; **or** package/truth present without required artefacts |
| Approved | `inspect_readiness`, `request_owner_review`, `stop` |
| Blocked | prep / validate-as-ready / submit |
| Owner-stop | Yes — `unsupported_state` |
| Audit | Flags / combination explanation; deny mutating proposals |

### 2.14 Supporting classes (also encoded)

| Class | Role |
|-------|------|
| `owner_approval_required` | Apply path needs prep but `owner_approvals_present == false` → stop `owner_approval_required` |
| `ready_for_owner_review` | Apply + artefacts + present package + truth PASS → stop `completed_for_owner_review` (owner review still mandatory) |

---

## 3. Implementation summary

| API | Role |
|-----|------|
| `AgentGoal` / `AgentRun` / `AgentStep` / `AgentAuditEvent` | Run + append-only audit shapes |
| `ReadinessSnapshot` / artefact / package / truth readiness | Derived observation |
| `ReadinessStateClass` + `primary_state_class` / `applicable_state_classes` | Classification |
| `AgentAction` / `AgentActionProposal` | Closed allow-list |
| `evaluate_action_policy` / `require_action_allowed` | Deterministic ToolPolicy |
| `AgentStopReason` | Fail-closed stops |
| `FORBIDDEN_ACTION_NAMES` | Explicit non-goals for proposers/docs |
| `new_agent_run_id` / `new_agent_step_id` / `new_agent_audit_event_id` | `agr_` / `ags_` / `aae_` ULID ids |

Public surface: `career_intelligence.agent`.

M1 does **not** implement AgentRuntime, ActionProposer providers, tool adapters,
CLI, persistence stores, or FR-016 handoffs.

---

## 4. Validation results

### Unit

`tests/unit/agent/` — **39 passed**.

| Check | Result |
|-------|--------|
| Id patterns / generators | Pass |
| Extra fields forbidden | Pass |
| Snapshot / package / truth consistency validators | Pass |
| Each required state class primary classification | Pass |
| ToolPolicy allow/deny matrices | Pass |
| Loop / max-steps / provider-down | Pass |
| Forbidden actions not in allow-list | Pass |
| Terminal AgentRun requires stop_reason | Pass |

```
python -m pytest tests/unit/agent/ -q
39 passed
```

---

## 5. Documentation updated

| Document | Change |
|----------|--------|
| ADR-007 | Accepted — BOPA; policy B; state classes; M1 scope |
| M0 spike | Marked Accepted with clarification |
| Functional specification | FR-015 M1 contracts |
| Domain model | Agent entities |
| Testing strategy | FR-015 M1 coverage |
| Implementation notes | FR-015 M1 notes |
| Roadmap / changelog | FR-015 M1 progress |
| AGENTS / ADR index / repository guide | Linked |

---

## 6. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Duplicate ULID helper vs truth/pipeline | Accepted | Avoids cross-package coupling |
| Snapshot builder from live SoT | Deferred | M2 |
| AgentRuntime / provider / CLI | Deferred | M2 / M3 |
| Persistence under `data/agent_runs/` | Deferred | M2 |
| Analyse/assess repair tools | Explicit non-goal | Diagnose/stop only unless future ADR |

---

## 7. Recommendations for M2

| Recommendation | Classification |
|----------------|----------------|
| AgentRuntime loop over ToolPolicy | M2 |
| ActionProposer port + one provider adapter | M2 |
| Thin adapters: preparation, package verify, truth validate | M2 |
| Build ReadinessSnapshot from Opportunity/package/truth services | M2 |
| Persist AgentRun JSON | M2 |
| Thin `cic agent` CLI | M3 |
| Adversarial injection fixtures | M4 |

---

## 8. Definition of Done (M1)

| Criterion | Status |
|-----------|--------|
| State-class matrix documented (owner clarification) | **Met** |
| Typed contracts + ToolPolicy in `career_intelligence.agent` | **Met** |
| ADR-007 accepted | **Met** |
| Unit tests for classification + policy | **Met** |
| No runtime / provider / CLI / FR-016 | **Met** |
