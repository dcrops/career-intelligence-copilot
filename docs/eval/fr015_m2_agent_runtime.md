# FR-015 M2 — Bounded Agent Runtime

**Date:** 2026-08-05  
**Status:** Complete (M2)  
**Architecture:** [ADR-007](../adr/007_bounded_agentic_workflow.md)  
**Preceding:** [M1 contracts](fr015_m1_agent_contracts.md)  
**Next:** M3 owner CLI — **complete** ([fr015_m3_owner_cli.md](fr015_m3_owner_cli.md))  
**Succeeded by:** [FR-015 acceptance](fr015_bounded_agentic_workflow.md)  
**Does not begin:** FR-016

---

## 1. Runtime architecture

```
AgentRuntime.start/resume(goal, owner_approvals_present)
        │
        ▼
┌──────────────────────────────────────────────┐
│ Loop (max_steps)                             │
│  1. ReadinessBuilder.build → snapshot        │
│  2. Classify ReadinessStateClass             │
│  3. Immediate stop if invalid/truth/ready/…  │
│  4. ActionProposer.propose (trusted flags)   │
│  5. evaluate_action_policy (ToolPolicy)      │
│  6. AgentActionExecutor.execute (thin)       │
│  7. Append AgentAuditEvent + checkpoint save │
└──────────────────────────────────────────────┘
        │
        ▼
Existing CIC services (authoritative)
```

Package: `career_intelligence.agent`  
Persistence: `data/agent_runs/{agr_*.json}` via `JsonDirectoryAgentRunStore`  
FR-008 is **not** invoked. Missing FR-002–005 → `invalid_state`.

---

## 2. Proposer contract / provider abstraction

| Type | Role |
|------|------|
| `ActionProposer` protocol | `propose(snapshot, approved_actions, primary_state_class) → (AgentActionProposal, ProviderMetadata?)` |
| `DeterministicActionProposer` | Preference table over approved actions (tests + offline) |
| `OpenAIActionProposer` | Structured parse; receives **only** readiness flags — never job-ad body |
| `StructuredActionProposal` | Pydantic schema for LLM output |

Invariant: proposer **suggests**; ToolPolicy **authorises**.

---

## 3. ToolPolicy behaviour (unchanged core + runtime use)

`evaluate_action_policy` still enforces:

- allow-list / state-class legality
- hard rules (prep needs apply + artefacts + approvals)
- repeated no-op (same action + same snapshot hash)
- max steps (stop still allowed at cap)

Runtime treats deny as fail-closed stop with audit `action_blocked`.

---

## 4. Adapter design

| Action | Adapter target |
|--------|----------------|
| `inspect_readiness` | No mutation — summarise snapshot |
| `run_preparation` | `ApplicationPreparationOrchestrator.run` |
| `verify_package` | `ApplicationPackageService.get(verify=True)` |
| `validate_truth_package` | `evaluate_package_truth(..., revalidate=True)` |
| `request_owner_review` / `stop` | Runtime stop only |

Idempotency: `run_preparation` / `validate_truth_package` skip when SoT already satisfies the outcome or the operation is recorded in `completed_operations`.

Forbidden: filesystem/shell/submit/pipeline/discovery/recruiter/truth waiver/FR-008 analyse tools.

---

## 5. Audit model

Append-only `AgentAuditEvent` kinds on each `AgentRun`:

`run_started` → `snapshot_observed` → `action_proposed` → `policy_evaluated` →
(`action_blocked` | `action_executed` + `service_result`) → `stop_recorded`

Also: `resume_observed`, `error_recorded`.  
`CompletedOperationRecord` tracks mutating successes for resume idempotency.  
Agent audit does **not** replace Opportunity / package / truth / submission / pipeline SoTs.

---

## 6. Loop and stop semantics

| Condition | Stop reason | Status |
|-----------|-------------|--------|
| Missing analysis/assessment/match/strategy | `invalid_state` | failed |
| Non-apply / contradictory | `unsupported_state` | failed |
| Truth fail / review_required | `truth_validation_blocked` | awaiting_owner |
| Ready (package + truth PASS) | `completed_for_owner_review` | awaiting_owner |
| Owner approvals missing for prep | `owner_approval_required` | awaiting_owner |
| Provider error | `provider_unavailable` | failed |
| Policy deny / loop | `policy_blocked` | failed / awaiting |
| Step budget | `max_steps_reached` | failed |

Default `max_steps=8`.

---

## 7. Checkpoint / resume

- Each step updates `checkpoint_ref` and persists the full `AgentRun`.
- `resume(agent_run_id)` requires `awaiting_owner` or `running`.
- First post-resume cycle forces `inspect_readiness` with `prior_agent_run_incomplete`.
- Snapshot is rebuilt from SoT; completed operations are not re-executed when already satisfied.

---

## 8. Prompt-injection safeguards

1. Proposer input excludes job-ad body (flags only).
2. Allow-list enum — unknown/forbidden names cannot execute.
3. ToolPolicy rejects illegal actions for state.
4. Adversarial fixtures: injected “submit/ignore instructions” rationale with illegal action → `action_blocked`.

---

## 9. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/agent/` (M1+M2) | **50 passed** |
| `tests/functional/test_fr015_m2_agent_runtime.py` | **2 passed** |

Coverage includes: invalid_state, happy path, truth block, injection deny, provider down, resume without re-prepare, idempotent skip, JSON store roundtrip, repeated-action block.

---

## 10. Manual validation

```
python scripts/run_fr015_m2_manual.py
```

**RESULT: PASS** (offline deterministic proposer)

| Journey | Result |
|---------|--------|
| A Happy path | PASS |
| B Missing analysis | PASS |
| C Truth fail | PASS |
| D Illegal proposal blocked | PASS |
| E Provider unavailable | PASS |

Evidence: `data/_fr015_m2_manual/summary.json`

---

## 11. Repository status

| Item | Status |
|------|--------|
| M0 spike | Accepted |
| M1 contracts + ADR-007 | Accepted / complete |
| **M2 runtime** | **Complete** |
| M3 CLI | Not started |
| FR-016 | Not started |

FR-008–FR-014 behaviour unchanged.
