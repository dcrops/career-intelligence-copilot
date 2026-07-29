# ADR-003: Application Workflow Orchestration Architecture

**Status:** Accepted  
**Date:** 2026-07-29

## Context

Horizon 1A requires coordinating job acquisition through analysis, assessment,
portfolio matching, application strategy, owner review, and (on apply) Opportunity
persistence without unsupervised submission. Phase 2 delivered FR-001–FR-007 as
typed public services. Before FR-008, orchestration was ad-hoc scripts and JSON
handoffs — no shared run state, checkpoints, or interrupt/resume model.

Candidates considered during the FR-008 learning spike:

1. **Thin in-repository runner** over Pydantic contracts (`career_intelligence.orchestration`)
2. **External workflow framework** (notably LangGraph)

M0–M3 produced concrete evidence: typed contracts (M0), deterministic graph +
JSON checkpoint resume + owner interrupt (M1), idempotent Opportunity side effects
on apply (M2), and bounded recoverable retries with fail-closed unknowns (M3).

## Decision

- Use a **thin in-repository** `ApplicationWorkflowRunner` as the FR-008 workflow
  runtime for the current single-user product phase.
- Keep **workflow-run checkpoints** (`CheckpointStore` / JSON under
  `data/workflow_runs/`) separate from the **Opportunity system of record**
  (ADR-002 / `data/opportunities/`).
- Represent one run as typed `WorkflowState` (control, acquisition envelope,
  domain artefact slots, approval, execution events, optional `RetryState`).
- Wrap FR-001–FR-005 (and M2 Opportunity) behind **node adapters** that call
  public service APIs only — no storage-adapter imports from orchestration.
- Route with an **inspectable deterministic sequence** (`next_spike_node` /
  completed-node labels). Do not introduce a general graph DSL yet.
- Require an **owner-review interrupt** before apply side effects; never default
  to apply; never silent-submit.
- Classify node failures as **recoverable** vs **unrecoverable**; unknown
  exceptions **fail closed**. Bound automatic retries to eligible LLM-backed
  nodes (`analyse`, `assess`) via injectable `RetryPolicy`. Persist attempt
  counts in checkpoints so process restart does not reset the budget.
- Prefer **source adapters** (paste/URL/API/feed/export) for acquisition;
  Playwright remains a controlled fallback adapter, not the default strategy.
- **Do not adopt LangGraph (or another orchestrator framework) now.**

## Evidence (M1–M3)

1. **Little machinery was required** — an explicit loop, node registry, and
   deterministic next-node function covered interrupt, resume, side effects, and
   retries without a framework.
2. **Checkpoint + resume** — JSON directory store preserved `run_id`, artefacts,
   approval, and retry state across process boundaries.
3. **Owner interrupt semantics** — `owner_review` completes when the interrupt is
   requested (`awaiting_owner`), not when the decision arrives; post-approval
   nodes are separate.
4. **Idempotent apply** — pre-allocate `opportunity_id`, checkpoint, then
   `create_from_strategy(opportunity_id=…)`; reclaim on resume; no duplicates
   under partial failure (M2; regression-tested after M3 retries).
5. **Bounded retries** — same-process and cross-process recovery for injected
   recoverable analyse/assess failures; exhaustion yields terminal `failed`
   without Opportunity creation; validation/trust-boundary failures are not
   retried.
6. **Separation of concerns** — Opportunity SoT unchanged; workflow checkpoints
   are recovery artefacts only.

## Why LangGraph is not required now

- The spike graph is linear with one mandatory interrupt and a small apply
  side-effect tail — not a large agent mesh.
- Typed Pydantic state + append-only events already provide auditability for the
  single-user phase.
- Framework adoption would add dependency, debugging, and mapping cost without
  changing FR-001–FR-007 service boundaries or ADR-002 persistence.
- Comparing syntax alone is insufficient justification; M1–M3 behaviour did not
  hit framework-shaped limits.

## Conditions to reconsider a framework later

Revisit only if several of the following become true:

- Many conditional branches / parallel fan-out that the thin runner cannot keep
  correct and inspectable
- Multiple durable human interrupts with complex re-entry semantics beyond
  owner-review + continue_run
- Need for managed distributed execution, multi-tenant isolation, or first-class
  tooling the in-repo runner cannot provide cost-effectively
- Bounded agents (FR-013+) require a shared runtime that the thin runner cannot
  host without becoming a de-facto framework itself

Any reconsideration must be a new ADR amending or superseding this decision,
backed by failing product evidence — not preference.

## Consequences

FR-008 can proceed to live source adapters and FR-009+ on this runtime without
blocking on LangGraph. Retry policy remains narrow (analyse/assess); post-approval
failures stay resumable via M2 idempotency rather than automatic policy retries.
Acquisition adapters must still respect provenance and fail-closed validation.

## Guardrails

- Do not import LangGraph (or equivalent) into production paths without a new ADR.
- Do not merge Opportunity SoT with workflow checkpoint storage.
- Do not retry deterministic validation or trust-boundary rejections by default.
- Do not silently submit applications or invent artefacts after failed attempts.
- Downstream code continues to use public profile / opportunity / analysis APIs —
  never YAML adapters from orchestration.
