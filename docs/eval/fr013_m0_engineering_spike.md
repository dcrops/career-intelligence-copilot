# FR-013 M0 — Application Pipeline Tracking Engineering Spike

**Status:** **Accepted** (owner 2026-08-05)  
**Date:** 2026-08-05  
**Phase:** Horizon 1A Stage 7  
**ADR:** [ADR-005](../adr/005_application_pipeline_lifecycle.md) (Accepted at M1)  
**Succeeded by:** [FR-013 M1 contracts](fr013_m1_pipeline_contracts.md)  
**Scope (M0):** Architecture only. No production implementation in this milestone.

**Preceding capability:** [FR-012 Submission Assistance](fr012_submission_assistance.md)
(complete and frozen — no `PipelineStatus` writes).  
**Next planned gate:** [FR-014 Recruiter Document Truth Validation](fr014_recruiter_document_truth_validation.md)
(automation-safety; does not block this spike).

**Builds on:** Phase 2 M2 decision/outcome logging (`OpportunityService.record_decision`
/ `update_outcome`; historically “FR-013 subset”); [ADR-002](../adr/002_opportunity_persistence.md);
[ADR-004](../adr/004_opportunity_review_boundary.md).

---

## 1. Executive Summary

Once an application package is generated and the owner submits (manually or via
FR-012 assisted attestation), CIC needs a **deterministic, auditable application
lifecycle** — tracking, not learning.

**Recommended answer to the key SoT question:**

| Concern | Owner |
|---------|--------|
| Business identity of the job candidate | **Opportunity** (`opp_<ULID>`) — unchanged ADR-002/004 |
| Current pipeline stage (queryable) | **Stored** on `Opportunity.status` (`PipelineStatus`) |
| Terminal / historical result summary | **Stored** on `Opportunity.outcome` (`OutcomeRecord`) |
| Audit of every advance / correction / evidence | **New append-only `PipelineEvent` log** keyed by `opportunity_id` |
| Submission mechanics audit | **SubmissionAttempt** (FR-012) — remains audit only |
| Package artefacts | **ApplicationPackageManifest** (FR-010) — referenced, never owns lifecycle |

Do **not** introduce a separate Application aggregate as a second system of record.
Do **not** put lifecycle on the package. Do **not** derive current status solely from
events while ranking/review already consume `Opportunity.status`.

FR-013 extends Phase 2 M2 from “overwrite status/outcome” into **lifecycle
management with immutable event evidence**, without redesigning FR-003/FR-004 or
feeding outcomes into scoring.

**Proposed ADR (on acceptance):** ADR-005 — Application Pipeline Lifecycle on
Opportunity (stored current state + append-only events; SubmissionAttempt remains
non-SoT).

---

## 2. Current Architecture

```
Acquire → Analyse → Assess → Match → Strategy → Owner Review (FR-008/009)
                                                      │
                              decision = apply / skip / defer
                                                      │
                         prepare package (FR-010/011)  │
                                                      │
                         submission assist (FR-012) ───┘
                              append-only SubmissionAttempt
                              ★ no PipelineStatus write
```

| Layer | What exists today | Lifecycle role |
|-------|-------------------|----------------|
| Opportunity (`data/opportunities/`) | Identity, decision, `status`, `outcome`, review, duplicates, artefacts | Business SoT; M2 status/outcome are mutable overwrites |
| `PipelineStatus` | `assessed` … `withdrawn` + allow-list transitions | Coarse operational stage; **not** advanced by FR-010–012 |
| `OutcomeRecord` | `outcome`, `interview_stage`, `follow_up_date`, `notes` | Summary fields; no history of changes |
| Application Package | Manifest under opportunity id | Generation artefact; regenerable |
| Submission Attempt | `data/submission_attempts/` | Submit audit only |
| Workflow checkpoints | `data/workflow_runs/` | Recovery only (ADR-003) |
| Review queue / recommendations | Derived projections | Already read `Opportunity.status` for open/urgency |
| `applications/application_tracker.csv` | Legacy operational tracker | Parallel memory; M3 import bridge only |

**Live store snapshot (spike date):** 15× `assessed`, 1× `interviewing` — dogfooding
has begun; most records never left assessment. Operational CSV still holds applied
rows outside structured pipeline discipline.

**Invariant already frozen by FR-012:** submission success must **not** silently
advance `PipelineStatus`. FR-013 owns that reporting boundary.

---

## 3. Problem Statement

Generation ends at package + optional submission audit. After real submissions,
the owner still needs:

1. A single authoritative **current stage** per applied opportunity.
2. An **auditable history** of how that stage changed (who/when/why/evidence).
3. Compatibility with existing ranking, review eligibility, and recommendations
   that already interpret `PipelineStatus`.
4. Continuity with `applications/` tracker semantics without a second competing
   pipeline database.
5. A design that later accepts FR-014 truth gates and FR-015 bounded agents as
   *writers of evidence*, not as redesigns of SoT.

Phase 2 M2 is insufficient alone: `update_outcome` mutates current fields with no
append-only transition log, interview granularity is a single enum overwrite, and
no first-class link exists from a successful `SubmissionAttempt` to a pipeline
advance. Terminal states cannot be corrected (fail-closed forever), which blocks
honest owner repairs.

**Out of scope for the problem (and for FR-013):** adaptive scoring, FR-003/004
redesign, dashboards, email, recruiter messaging, automation of submission.

---

## 4. Alternative Architectures

### A. Opportunity-only (extend M2 in place)

Keep `status` / `outcome` on Opportunity; enrich fields; no event log.

- **Pros:** Minimal surface; ranking already works.
- **Cons:** No real audit; corrections destroy history; weak FR-015 evidence trail.

### B. New Application aggregate (second SoT)

`app_<ULID>` owns lifecycle; Opportunity stays pre-apply catalogue.

- **Pros:** Clean “application process” noun; 1:N applications per opportunity later.
- **Cons:** Splits SoT with `Opportunity.status`; package/submission already key by
  `opportunity_id`; dual status drift; contradicts ADR-004 “one business SoT”.
  Premature — today’s product is one apply-process per opportunity identity.

### C. Package-owned lifecycle

Lifecycle hangs off `ApplicationPackageManifest`.

- **Pros:** Ties progress to artefacts submitted.
- **Cons:** Regeneration / re-prepare must not reset pipeline; package is a versioned
  artefact, not a process. Rejected.

### D. Pure event sourcing (derived status only)

Append-only events; current status always projected.

- **Pros:** Maximum audit purity.
- **Cons:** Every consumer (comparison, review queue, recommendations, CLI show)
  must project; risk of projection bugs becoming business bugs; heavier than needed
  for single-user YAML store.

### E. Hybrid (recommended) — Opportunity current state + append-only pipeline events

Opportunity remains the only business SoT. Current `status` / `outcome` stay stored
for queries. Every transition and material evidence write appends a `PipelineEvent`.
SubmissionAttempt and package refs are **linked evidence**, not lifecycle owners.

- **Pros:** Matches ADR-002/004; matches FR-009 `review_actions` pattern; preserves
  ranking; gives FR-014/015 an audit spine; allows controlled corrections.
- **Cons:** Must keep stored status and latest event projection consistent
  (service-enforced single writer).

### F. CSV / `applications/` as SoT

- **Rejected:** Operational continuity requires *connecting to* the tracker, not
  making the CSV authoritative. Structured store already won (ADR-002 Option C).

---

## 5. Trade-off Analysis

| Criterion | A In-place | B New Application | D Pure events | **E Hybrid** |
|-----------|------------|-------------------|---------------|--------------|
| Single business SoT | Yes | No | Yes (events) | **Yes** |
| Auditability | Weak | Strong if done well | Strong | **Strong** |
| Ranking / review compatibility | Immediate | Migration / dual read | Projection tax | **Immediate** |
| Package regeneration safety | N/A | OK | OK | **OK (refs only)** |
| FR-012 attempt separation | OK | OK | OK | **OK** |
| Correction / reopen | Hard | Designable | Natural | **Designable** |
| Implementation cost | Lowest | Highest | High | **Medium** |
| Premature abstraction | Low | High | Medium | **Low** |

**Decision:** Alternative **E**.

---

## 6. Recommended Architecture

```
Opportunity (SoT)
  ├── decision, review, duplicate          (orthogonal — ADR-004)
  ├── status: PipelineStatus               (stored current stage)
  ├── outcome: OutcomeRecord               (stored summary)
  └── pipeline_events[]  OR  data/pipeline_events/{opp_id}/
        append-only PipelineEvent records

ApplicationPackageManifest  ──referenced by──► PipelineEvent.evidence
SubmissionAttempt           ──referenced by──► PipelineEvent.evidence

Owner
  → PipelineTrackingService (name indicative)
       → validate transition
       → append PipelineEvent
       → update Opportunity.status / outcome atomically (logical)
  → thin CLI later (not designed in detail here)
```

### Architectural rules

1. **Opportunity owns lifecycle identity.** One applied opportunity ⇒ one pipeline.
2. **Stored current + append-only history.** Never status-only without an event for
   owner-visible advances (service invariant).
3. **SubmissionAttempt never writes PipelineStatus** (FR-012 freeze held). FR-013
   may *offer* an owner operation that advances status **citing** a successful
   attempt id.
4. **Package never owns status.** Events may record `package_prepared_at` / hash /
   artefact paths as evidence of what was sent.
5. **Decision ≠ status ≠ outcome ≠ review archive.** Preserve M2/ADR-004 separations.
6. **Tracking ≠ learning.** No feedback into FR-003/004 in this FR.
7. **Manual-first.** Tracking begins when the owner records that an application was
   submitted (or cites an FR-012 manual/assisted completion). No silent automation.

### New ADR warranted?

**Yes (on acceptance).** FR-012 explicitly left PipelineStatus to FR-013; hybrid
audit amends how M2 lifecycle fields behave. Draft title: **ADR-005 Application
Pipeline Lifecycle (stored status + append-only events)**.

---

## 7. Domain Model

### 7.1 Entities and concerns

| Concept | Persistence | Notes |
|---------|-------------|-------|
| Opportunity | `data/opportunities/` | Unchanged identity; gains richer lifecycle discipline |
| PipelineStatus | Field on Opportunity | Coarse stage — see §8 |
| OutcomeRecord | Field on Opportunity | Result summary — keep distinct from status |
| InterviewStage | Field on OutcomeRecord | Interview *granularity* without exploding status enum |
| PipelineEvent | New append-only store or tuple on Opportunity | Immutable transition/evidence record |
| SubmissionAttempt | Existing | Linked evidence for submit events |
| ApplicationPackage | Existing | Linked evidence for prepare/submit events |
| OwnerDecision / Review | Existing | Out of FR-013 mutation scope except reading apply eligibility |

### 7.2 PipelineEvent (proposed contract shape)

Indicative fields (freeze in M1, not here):

| Field | Role |
|-------|------|
| `event_id` | `ple_<ULID>` |
| `opportunity_id` | Parent SoT key |
| `occurred_at` | Event time (owner-asserted or system) |
| `recorded_at` | Write time |
| `kind` | e.g. `status_transition`, `outcome_update`, `evidence_added`, `correction`, `note` |
| `from_status` / `to_status` | When kind advances stage |
| `outcome` / `interview_stage` | Optional summary deltas |
| `evidence` | Structured refs + freeform note (see § evidence) |
| `actor` | `owner` (default); future `agent:<id>` for FR-015 without redesign |
| `supersedes_event_id` | Optional — corrections point at prior event; never delete |

### 7.3 What is *not* a new entity

- **Application** as aggregate — deferred until a proven 1:N need (re-apply cycles
  with separate legal applications) appears.
- **Pipeline queue** store — active pipeline lists are derived from Opportunities
  (same pattern as review queue).

---

## 8. Lifecycle State Diagram

### 8.1 Design choice: coarse status + fine interview stage

The example chain (Discovered → … → Final interview → …) mixes **catalogue**,
**owner decision**, **preparation**, and **employer process**. Those concerns are
already split in CIC. FR-013 should **not** collapse them into one mega-enum.

| Phase | Already owned by | FR-013 role |
|-------|------------------|-------------|
| Discovered / analysed | Opportunity create | Pre-pipeline |
| Reviewed / apply approved | Review + `decision` | Pre-pipeline gate |
| Package generated | FR-010/011 | May emit evidence event; status may move to `preparing` |
| Submitted | FR-013 (+ cite FR-012) | Advance to `submitted` |
| Employer process | FR-013 | `interviewing` / `offer` + `InterviewStage` |
| Terminal | FR-013 | `accepted` / `rejected` / `withdrawn` |
| Archived (hide from review) | FR-009 `archived_at` | **Not** a pipeline status |

### 8.2 Recommended `PipelineStatus` (evolve existing; do not explode)

Retain the M2 vocabulary with clarified meaning:

```
assessed ──► deferred ──► preparing ──► submitted ──► interviewing ──► offer
   │            │            │             │              │              │
   └────────────┴────────────┴─────────────┴──────────────┴──────────────┼──► withdrawn
                                                                         ├──► rejected
                                                                         └──► accepted (from offer)
```

| Status | Meaning |
|--------|---------|
| `assessed` | Analysed; not in active apply execution |
| `deferred` | Owner paused apply execution (distinct from review `defer_until`) |
| `preparing` | Apply decided; package/work in progress |
| `submitted` | Owner asserts application sent (evidence required) |
| `interviewing` | Any live interview loop; detail in `InterviewStage` |
| `offer` | Offer received (not yet accepted) |
| `accepted` | Terminal positive |
| `rejected` | Terminal employer/process rejection |
| `withdrawn` | Terminal owner withdrawal |

**Explicitly not added as statuses in FR-013:** `acknowledged`, `recruiter_contact`,
`phone_screen`, `technical`, `final`, `archived`. Encode acknowledgements and round
detail as **events + `InterviewStage` / notes**. Add statuses later only with owner
approval if reporting proves the coarse model inadequate.

### 8.3 `InterviewStage` (keep; optionally extend in M1)

Current: `none | recruiter | hiring_manager | technical | other | unknown`.

Spike recommendation: **keep** for FR-013 M1. If dogfooding needs “final”, add
`final` in a later milestone rather than inventing parallel status values now.

### 8.4 Allowed transitions (policy intent)

Extend M2 allow-list; same-status allowed for outcome-only / evidence-only updates.

| From | Allowed to |
|------|------------|
| `assessed` | `deferred`, `preparing`, `submitted`, `withdrawn` |
| `deferred` | `assessed`, `preparing`, `submitted`, `withdrawn` |
| `preparing` | `submitted`, `deferred`, `withdrawn` |
| `submitted` | `interviewing`, `offer`, `rejected`, `withdrawn` |
| `interviewing` | `interviewing` (stage change), `offer`, `rejected`, `withdrawn` |
| `offer` | `accepted`, `rejected`, `withdrawn` |
| Terminal | **no silent exit** — see corrections |

**Invalid examples:** `assessed` → `interviewing`; `preparing` → `offer`;
`rejected` → `submitted` without correction protocol; any FR-012 adapter writing
status directly.

**Skip-forward:** `assessed`/`preparing` → `submitted` remains allowed (owner may
track without using preparing). Prefer evidence when skipping.

---

## 9. Event Model

### 9.1 Append-only with stored current state

| Question | Answer |
|----------|--------|
| Is every transition an immutable event? | **Yes** for owner-visible advances and corrections |
| Is current state derived? | **No** — stored on Opportunity for consumers |
| Consistency rule | Pipeline service appends event **and** updates stored fields in one logical write; readers never “fix” events for current status |
| Corrections | Append `correction` / `reopen` events; optionally `supersedes_event_id`; update stored state; **never delete** prior events |
| Terminal reopen | Allowed only via explicit correction (e.g. mistaken `rejected`); requires note; audited |

This mirrors FR-009 (`review` current + `review_actions` history) and FR-012
(append-only attempts), without turning Opportunity into pure event source.

### 9.2 Event kinds (indicative)

| Kind | When |
|------|------|
| `status_transition` | Stage changes |
| `interview_stage_change` | Fine-grained interview progress without status change |
| `outcome_change` | `pending` → `rejected` / `offer` / etc. |
| `evidence_added` | Link package, attempt, URL, note without stage change |
| `follow_up_set` | Follow-up date changes |
| `correction` | Owner amends prior mistaken transition |
| `note` | Reflection without structural change |

### 9.3 Relationship to SubmissionAttempt

A successful FR-012 attempt is **necessary evidence for a clean submit story**, not
an automatic status write. Recommended owner path:

```
FR-012 terminal success / manual_completed
  → owner runs FR-013 “record submitted” (citing attempt_id)
  → PipelineEvent(status submitted) + Opportunity.status = submitted
```

Failed / `outcome_unknown` / `manual_action_required` attempts do **not** advance
pipeline; they remain submission audit. Recovery attempts stay on FR-012; pipeline
stays at prior stage until the owner records success.

---

## 10. Persistence Recommendation

### Compare

| Option | Verdict |
|--------|---------|
| Only fields on Opportunity index row | Reject for audit (A) |
| Events embedded as growing tuple on Opportunity YAML | Acceptable early; index rewrite cost grows |
| **Sibling store `data/pipeline_events/` keyed by opportunity_id** | **Preferred** — mirrors submission_attempts; keeps index lean |
| New database / service process | Reject — single-user YAML era |
| Inside Application Package directory | Reject — wrong aggregate |

**Recommendation:**

- Keep `Opportunity.status` / `outcome` in `data/opportunities/index.yaml`.
- Persist append-only events under `data/pipeline_events/{opportunity_id}/`
  (JSON files or one JSONL per opportunity — decide in M1).
- Public API via `career_intelligence.pipeline` (name indicative) that **calls**
  `OpportunityService` for status writes — do not bypass OpportunityStore.
- No second business SoT.

**Operational continuity:** Provide export/sync *toward* `applications/application_tracker.csv`
semantics in a later milestone (status mapping already exists in M3 legacy import).
Do not make CSV authoritative.

---

## 11. Service Boundaries

| Component | Owns | Does not own |
|-----------|------|--------------|
| `PipelineTrackingService` (indicative) | Transition policy, event append, status/outcome updates, evidence validation | Package rules, submission adapters, review queue, scoring |
| `OpportunityService` | Opportunity aggregate persistence; may expose low-level save used by pipeline service | Event schema policy (prefer pipeline package owns events) |
| `SubmissionOrchestrator` (FR-012) | Submit attempts | PipelineStatus |
| `ApplicationPackageService` (FR-010) | Package integrity | Lifecycle |
| `ApplicationPreparationOrchestrator` (FR-011) | Prep sequencing | Lifecycle |
| FR-008 runner | Acquisition through decision | No submit/pipeline nodes in FR-013 |
| Review / recommendations | Read status for eligibility/urgency | Write pipeline |
| Thin CLI (`cic pipeline` — indicative) | Parse / present | Policy |

**Pattern:** Same as FR-011/012 — dedicated coordinator/service for the concern;
CLI is interface only; existing SoT unchanged in meaning.

---

## 12. Risks

| Risk | Mitigation |
|------|------------|
| Dual write drift (event vs status) | Single service path; tests that every status change requires an event |
| Inflating status enum | Prefer events + InterviewStage; require owner approval to add statuses |
| Confusing review archive with withdrawn/rejected | Docs + API naming; archive stays FR-009 |
| Confusing SubmissionAttempt success with pipeline submitted | Keep FR-012 freeze; explicit FR-013 record-submitted |
| PII creep (recruiter names/emails) | Optional evidence fields; never copy network tracker PII into docs/rules; minimise required evidence |
| Premature Application entity | Defer until 1:N re-apply is real |
| Learning pressure (“use rejects to retrain FR-003”) | Explicit out of scope; Horizon 2 / future FR |
| Terminal immutability vs honest corrections | Explicit correction/reopen protocol with notes |
| Dogfooding divergence (CSV vs CIC) | Later milestone: export / guided migration; owner still decides |

---

## 13. Future Compatibility

### FR-014 — Recruiter Document Truth Validation

- Truth validation gates **artefact approval before submit**, not pipeline stages.
- Pipeline events may later *reference* a truth-report id as evidence that the
  submitted package passed validation — additive evidence, no SoT change.
- FR-013 must not embed claim-checking in lifecycle transitions.

### FR-015 — Bounded Agentic Workflow

- Agents become additional `actor` values that propose or record events under
  owner approval gates.
- Append-only events + stored status give agents a readable world model without
  inventing a new aggregate.
- Do not put agent orchestration inside the pipeline service.

### Later reporting / Horizon 2 learning

- Event log enables time-in-stage and funnel metrics without redesign.
- Feeding outcomes into assessments remains a **separate** FR — architecture does
  not block it, and does not implement it.

---

## 14. Engineering Spike Conclusion

| Question | Conclusion |
|----------|------------|
| What owns lifecycle after generation? | **Opportunity** (business identity + stored current stage) |
| What provides audit? | **Append-only PipelineEvent log** |
| New Application entity? | **No** (not now) |
| Package as lifecycle owner? | **No** |
| SubmissionAttempt as lifecycle owner? | **No** (evidence only) |
| Transitions | Deterministic allow-list; append-only events; corrections via new events |
| Current state | **Stored**, not solely derived |
| Manual-first | Owner records submit / stage moves; no silent FR-012 advance |
| Learning / FR-003 | Out of scope |
| ADR | **Propose ADR-005** on acceptance |

**GO recommendation (engineering):** Accept this spike as FR-013 M0 foundation.
Proceed to M1 contracts only after owner acceptance.

**Outcome:** **Accepted** 2026-08-05 — see Owner Acceptance below. M1 delivered:
[fr013_m1_pipeline_contracts.md](fr013_m1_pipeline_contracts.md).

---

## 15. Recommended Milestones

| Milestone | Intent | Deliverables | Explicit non-goals |
|-----------|--------|--------------|--------------------|
| **M0** | Engineering spike | This document; owner accept/reject | Code, tests, roadmap edits |
| **M1** | Domain contracts | `PipelineEvent` model; transition table; evidence schema; store protocol; ADR-005 draft/accept; unit tests for transitions/events only | CLI, FR-012 bridge behaviour, reporting |
| **M2** | Executable tracking | `PipelineTrackingService`; record submitted / advance / outcome / note / correction; Opportunity status writes only via service; persistence under `data/pipeline_events/` | Dashboards, automation, CSV sync |
| **M3** | Owner workflow + bridges | Thin `cic pipeline` (indicative ops below); cite SubmissionAttempt + package evidence; optional advance-from-attempt helper; migrate/guide live dogfood records | Live board automation, agent writers |
| **M4** | Continuity & reporting projections | Derived pipeline views (active / by status); time-in-stage from events; export alignment with `applications/application_tracker.csv` semantics | UI dashboard, adaptive scoring |
| **Close-out** | Freeze | Acceptance report; docs freeze; no reopen without owner request | — |

### Likely owner operations (CLI shape deferred)

- Record submitted (with evidence)
- Advance status / interview stage
- Record outcome / rejection reason / offer note
- Set follow-up
- Add note / evidence
- Correct / reopen (explicit)
- Show current + event history
- List active pipeline

---

## 16. Definition of Done

### M0 (this spike) — Done when

| Criterion | Status |
|-----------|--------|
| Spike document covers architecture questions 1–12 from the brief | **Met** (this file) |
| Recommended SoT and alternatives recorded | **Met** |
| State model, transitions, event/persistence/service boundaries recorded | **Met** |
| Milestones M0–M4 + close-out proposed | **Met** |
| No production code / tests / roadmap edits in M0 | **Held** |
| Owner accepts or requests revisions | **Accepted** 2026-08-05 |

### FR-013 overall (later close-out) — Done when

| Criterion | Target |
|-----------|--------|
| ADR-005 accepted (or explicit decision recorded if ADR waived) | Close-out |
| State transitions auditable with timestamps | Spec AC |
| Owner can see current pipeline status per opportunity | Spec AC |
| Failed submission / recovery remain on FR-012; pipeline records owner-attested progress | Spec AC |
| Outcomes recordable against opportunities (M2 retained and extended) | Spec AC |
| Unit + functional tests; manual validation harness | Close-out |
| Docs: functional spec, domain model, implementation notes, testing strategy, changelog, roadmap | Close-out |
| No FR-003/004 redesign; no adaptive scoring; no UI dashboard | Held |
| Owner review of freeze report | Close-out |

---

## Evidence Evaluation (brief §8)

| Evidence | FR-013 stance |
|----------|---------------|
| Submission date / recorded_at | **Required** on submit transition |
| Application channel | **Recommended** (may cite attempt.channel) |
| Package prepared_at / hash / artefact refs | **Recommended** on submit |
| SubmissionAttempt id | **Recommended** when FR-012 used |
| Job URL | Prefer Opportunity identity `canonical_url` / `source_url`; don’t duplicate unless correction |
| CV / cover letter versions | Via package manifest refs — not parallel version SoT |
| Interview feedback / rejection reason / offer details | **Optional structured notes** on events/outcome; keep schemas small |
| Recruiter identity | **Optional**; minimise; do not import network PII into docs |
| Salary | **Out of core** until Opportunity gains real salary fields (never invent) |
| Owner reflections | Notes/events — allowed |
| Learning features from outcomes | **Out of scope** |

---

## Reporting Implications (architecture only)

Natural projections from stored status + events (M4+):

- Counts by status / month (submit cohort)
- Interview rate / offer rate / time-in-stage
- Active pipeline health (submitted + interviewing + offer)
- Company activity via Opportunity identity facets

No dashboard work in FR-013. Ensure event timestamps and status vocabulary make
these queries possible without schema rework.

---

## Owner Workflow Map

```
Generate package (FR-010/011)
  → Owner review artefacts (+ future FR-014 truth gate)
  → Render HTML/PDF (render-only)
  → Submit manually and/or FR-012 assisted / record-manual
  → ★ FR-013: record submitted (cite attempt + package evidence)
  → Track interviewing / offer / terminal outcomes with events
  → Optional: export / align operational tracker (M4)
```

Pre-submit catalogue work (discover → assess → decide → prepare) remains FR-008–011.
FR-013 starts at **owner-attested application progress**, with optional `preparing`
as the bridge from apply decision into execution.

---

## Owner Acceptance (2026-08-05)

| Decision | Result |
|----------|--------|
| Hybrid architecture (Opportunity current state + append-only PipelineEvents) | **Accepted** |
| Coarse `PipelineStatus` + separate `InterviewStage` (no mega-enum) | **Accepted** |
| Milestone split M0–M4 | **Accepted** |
| Authorise ADR-005 at M1 | **Accepted** |

**Additional invariant (owner):** SubmissionAttempt success does **not**
automatically advance `Opportunity.status`. Pipeline advancement is an explicit
owner action. Corrections are new events — never mutation or deletion of prior
events. Recorded in [ADR-005](../adr/005_application_pipeline_lifecycle.md).
)
