# Engineering Principles

## Purpose

This document defines how engineering decisions should be made throughout Phase 2 and beyond.

It complements [03_product_vision.md](03_product_vision.md) (what the product believes) and [04_functional_specification.md](04_functional_specification.md) (what the system must do). It does not choose technologies, propose architecture, or describe implementation.

For agent bootstrap instructions, see [AGENTS.md](../AGENTS.md).

---

## Decision Context

Every engineering tradeoff in this repository is made under constraints that do not apply to typical product teams:

- **Horizon 1 urgency** — the owner is running an active job search with real deadlines
- **Single builder** — the user, product owner, and engineer are the same person
- **Three objectives** — career outcome, portfolio demonstration, and Cursor workflow learning compete for time; Horizon 1 wins on conflict
- **Phase 2 baseline** — Job Intelligence MVP is complete and frozen; Horizon 1A
  work should earn architectural change rather than casually reopening settled
  Phase 2 decisions
- **Horizon 1A before 1B** — job application workflow before recruiter outreach

---

## Invariants

These are non-negotiable unless the owner explicitly revises them and the changelog is
updated. Phase 2 established them in practice; they continue to bind Horizon 1 work.

### Job acquisition first; recruiter outreach second

Complete the discover → assess → prepare → review → submit → track loop before
investing in recruiter discovery, outreach messaging, meetup intelligence, or LinkedIn
network automation. Recruiter work is an additional acquisition channel once the
application loop is reliable — not a parallel distraction.

### Validate first, change second

Reproduce and understand current behaviour before changing planners, prompts,
adapters, or workflow graphs. Spikes use saved/manual jobs before live acquisition.

### Deterministic first; agents only when justified

Prefer deterministic workflow nodes and typed services where decisions are already
understood. Introduce bounded agents (FR-015 — **complete / frozen**) only after the
deterministic path (FR-008) works; multi-agent patterns (FR-016 — **complete / frozen**
as a learning proof only; prefer `cic agent run` for ordinary prep) only after bounded
agents are reliable. Do not blur workflow orchestration with agent reasoning.

**Orchestration coordinates; services execute; adapters channel; interfaces remain thin.**
A dedicated coordinator (FR-011 preparation, FR-012 submission) sequences existing
public services and keeps business rules inside those services. Channel adapters
execute external/offline actions only. Owner-facing CLIs map commands to the
coordinator — they do not duplicate eligibility, gates, or document generation.
Established by FR-011
([eval/fr011_application_preparation.md](eval/fr011_application_preparation.md))
and confirmed by FR-012
([eval/fr012_submission_assistance.md](eval/fr012_submission_assistance.md)).
**FR-013** confirms the same thin-CLI pattern for lifecycle:
`cic pipeline` → `PipelineTrackingService` (event-first dual-write; no silent submit;
SubmissionAttempt never auto-advances status —
[eval/fr013_application_pipeline_tracking.md](eval/fr013_application_pipeline_tracking.md);
[ADR-005](adr/005_application_pipeline_lifecycle.md)).

**Append-only submission audit; never silent submit.** SubmissionAttempt identity is
never deleted; uncertain outcomes fail closed; Owner Approval is distinct from apply /
package / document gates.

**Append-only pipeline audit; Opportunity remains current-state SoT.** PipelineEvents
are immutable; corrections are new events; legacy Phase 2 M2 `update_outcome` may
still write status without events (accepted debt — owner path is `cic pipeline`).

**Recruiter-document truth is a deterministic fail-closed boundary (FR-014 — complete).**
Detection certainty is distinct from evidence validation
([ADR-006](adr/006_recruiter_document_truth_validation.md)). PASS requires complete
coverage and performed detection + validation. JD / assessment / strategy / plans never
authorize candidate capability. Claim kinds in force: technology, employment honesty,
certification, duration, project delivery, domain — not soft skills or subjective prose.
Truth Validation does not rewrite or replace owner review. Fresh content-hash reports
gate package external use and submission.

### Intelligence before automation

Decision quality is the product. Automation serves intelligence — it does not replace it. Automate structured extraction and comparison; do not automate tier commitment or externally visible actions.

### Human review on consequential outputs

Tier recommendations, ranked comparisons that drive daily effort, application packages,
and any submission or externally visible content require user review and override
capability. Application tiers are effort guidance only — they are not autonomous
apply/skip decisions. **Never silently submit an application.**

### Fail closed on uncertain external actions

Where a required application answer is unknown or materially uncertain — or CAPTCHA,
auth, or unsupported forms block a safe path — fail closed and escalate to the owner.
Do not fabricate answers.

### Dual-value gate

Every capability must satisfy at least one criterion from [04_functional_specification.md](04_functional_specification.md) § Prioritisation Guidance. If neither applies, defer.

### Explainability and evidence

Assessments must be explainable with cited evidence. Do not ship confident-sounding outputs without grounding. Do not invent precision (scores, percentages) where evidence is insufficient.

### Outcome logging

Pipeline and outcome recording (Phase 2 M2; Horizon 1A **FR-013**) is infrastructure,
not a backlog item. A system that assesses but does not remember is a calculator,
not a copilot. Submission attempt audit (FR-012) is separate from pipeline lifecycle.
**ADR-005:** Opportunity stores current `PipelineStatus`; append-only `PipelineEvent`s
audit changes; SubmissionAttempt success never auto-advances status — owner action
only; corrections are new events.

### Operational continuity

The built system must connect to the owner's existing workflow in `applications/` and related operational folders. A parallel tool that the owner must maintain alongside manual trackers has failed regardless of technical quality.

### Explicit provenance and adapter isolation

Acquisition, intelligence, preparation, submission, and tracking are separate concerns.
Unstable external systems (email, boards, browsers) sit behind adapters with typed
outputs, extraction warnings, and tests. Playwright is a controlled fallback — not the
default acquisition architecture and not an excuse for crawlers or access-control bypass.

### Orchestration learning transparency

Horizon 1A teaches agent orchestration progressively. Each orchestration feature must
document engineering reason, pattern, alternatives, deterministic-vs-agentic choice,
owner learning concept, manual validation, and mastery evidence. Opaque “install a
framework and wire agents” guidance is unacceptable. Production commitment to LangGraph
(or any orchestrator) requires an ADR. **ADR-003 is accepted** for the current scope:
thin in-repository runner; revisit only under conditions in that ADR.

### Auditable, idempotent state transitions

Workflow and pipeline transitions should be observable, preferably idempotent, and
resumable across owner-approval interrupts. Prefer checkpoints over silent retries that
duplicate submissions.

### Persist analysed work before asking the human

Where a human interrupt sits in the middle of a workflow, write the durable record
*before* the interrupt and update it with the decision afterwards — create then update,
not decide then create. Completed analysis is expensive and the pause is unbounded, so a
"no" must leave evidence rather than nothing. Idempotency comes from pre-allocating the
record's identity and checkpointing it before the write, so a replay reclaims the record
instead of creating a second one. Established by FR-009 M1
([ADR-004](adr/004_opportunity_review_boundary.md)).

### Derive views; persist facts

Owner-visible orderings, bands, and labels should be computed from persisted facts, not
stored alongside them. A stored rank or eligibility flag must then be invalidated and
reconciled on every change to the underlying record, which is how two sources of truth
begin. Date-sensitive policy takes an explicit reference date rather than reading the
clock, so behaviour is testable and explanations are reproducible.

### Reversible owner overrides stay orthogonal to decisions

Owner presentation controls (pin, archive, reviewed, defer-until) must be reversible and
must not silently rewrite owner decisions, fit ranking inputs, or application-pipeline
status. Prefer idempotent repeats over errors for harmless double-clicks. When a reverse
action clears prior state (for example clearing a defer), keep lightweight audit evidence
so the history is not lost — without turning the aggregate into an event-sourced system.

### Link records; never merge them

When two records may describe the same real-world thing, weigh the failure modes rather
than the match score. A wrong merge silently removes a real item from the owner's view and
is hard to notice or undo; a duplicate left visible costs a glance. So detect
deterministically, show matching *and* differing evidence, let the owner confirm, and
represent the outcome as a relationship between preserved records. Treat data absent on
either side as unknown, never as agreement, and never let a single weak signal (a shared
content hash) stand in for identity. Record rejected suggestions too, so the same question
is not asked twice. Established by FR-009 M3
([ADR-004](adr/004_opportunity_review_boundary.md)).

### Rank on evidence you actually hold

Prioritisation should be an ordered key of named signals, not a composite score: the owner
must be able to see why A outranks B and challenge the policy. Rank on what the capability
is for — opportunity quality and owner value — and keep cost signals (effort tier) as
context rather than ranking factors. Absent evidence must never improve a position: score
`unknown` as zero and report the gap. Never manufacture a signal the record does not hold
(closing dates, salary) in order to produce urgency. Established by FR-009 M4
([ADR-004](adr/004_opportunity_review_boundary.md) Decision 8).

---

## Tradeoff Principles

### Scope control

Horizon 1A owns the application workflow (FR-008–FR-017). Resist Horizon 1B recruiter
modules, dashboards, and unofficial presentation polish that displace acquisition and
submission. FR-006/FR-007 document generation is complete; do not reopen for polish
while the application loop is incomplete.

**Violate when:** An addition passes the dual-value test, has an approved FR (or explicit
owner request), and accelerates Horizon 1A without delaying the application loop.

### Simplicity over flexibility

Optimise for one user, one search context, one profile. Generalise only at stage boundaries (see Extensibility), not inside implementations.

**Violate when:** Simplicity would force false precision — e.g. a single opaque score instead of dimensional fit breakdown.

### Build before automate

Manual confirmation steps are acceptable during early delivery. Trust the assessment loop before collapsing review steps.

**Violate when:** A manual step becomes the adoption bottleneck and the automated step has verifiable correctness with optional review.

### Acceptable technical debt

Acceptable: rough ingestion, manual profile bootstrapping, minimal comparison UI.

Unacceptable: unreproducible assessments, missing outcome records, unexplained tier logic, duplicated operational data in incompatible formats.

**Violate when:** Debt on the critical path to first useful assessment on a real posting this week — if the reasoning chain is sound and outcomes are logged.

### Performance

Optimise time-to-decision for occasional interactive use — a few assessments per day — not throughput or scale.

**Violate when:** Slow assessments cause the owner to bypass the system and revert to manual analysis.

### Testing

Prioritise decision regression over code coverage. Golden cases should come from real postings in the application tracker. One visibly wrong assessment on a cared-about role ends adoption.

**Violate during:** Initial exploration before assessment shape stabilises. Non-negotiable once tiers influence real decisions.

### MVP discipline

Ship the smallest complete loop: profile → analysis → assessment → tier → log → compare. Breadth without a complete loop is not MVP.

**Violate when:** The loop is complete but unused because it does not connect to where the owner already works — extend only enough to bridge adoption, not to add features.

### Extensibility

Build extensible seams between decision stages; keep implementations inside each stage simple. Outcome records and assessment objects should be shaped so future phases can consume them.

**Violate when:** An abstraction serves only Horizon 2, has no Phase 2 consumer, and delays delivery.

---

## Common Failure Modes

Avoid these patterns — they are the most likely causes of project failure in this repository:

1. **Starting recruiter outreach (Horizon 1B) before the application loop works** —
   messaging and networking feel urgent but displace job acquisition, ranking, and
   reviewed submissions
2. **Treating acquisition as “web scraping”** — crawlers, brittle selectors, and
   access-control bypass create fragile, non-compliant systems
3. **Agents before deterministic workflow** — multi-agent theatre without typed state,
   approvals, and recoverable nodes
4. **Silent or fabricated submission answers** — destroys trust and creates legal/ethical risk
5. **Confident assessments without evidence** — erodes trust after one bad recommendation
6. **A system parallel to existing trackers** — the owner maintains two workflows; the manual one wins
7. **Optimising portfolio or learning over Horizon 1A** — impressive engineering that does not shorten time-to-submitted applications
8. **Skipping outcome / pipeline logging** — no compounding value, repetitive re-work

---

## Relationship to Other Documents

| Question | Authoritative document |
|----------|------------------------|
| What must the system do? | [04_functional_specification.md](04_functional_specification.md) |
| What phase are we in? | [10_roadmap.md](10_roadmap.md) |
| What are the domain entities? | [06_domain_model.md](06_domain_model.md) |
| What are the product principles? | [03_product_vision.md](03_product_vision.md) |
| Why did decisions change? | [11_changelog.md](11_changelog.md) |

When this document conflicts with the functional specification on requirements, the functional specification wins. When it conflicts on how to prioritise engineering effort, this document wins.

---

## Updating This Document

Record engineering invariant changes here and in [11_changelog.md](11_changelog.md). Do not leave durable tradeoff decisions only in agent conversations.

Architecture Decision Records live in `docs/adr/`. **ADR-003 (orchestration
architecture)** is **accepted**: thin in-repository runner; LangGraph not required
for the current FR-008 scope. See
[003_application_workflow_orchestration.md](adr/003_application_workflow_orchestration.md).
Reconsider only under the conditions recorded in that ADR.
