<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/eval/fr018_m0_engineering_spike.md
Mode: full-file snapshot
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

# FR-018 M0 — Opportunity Discovery & Acquisition Engineering Spike

**Status:** **Complete (M0 spike)** — **Accepted** by owner; unlocked M1;
**GO to M1 under narrow scope** (URL-first executable path); M1 later redefined by
owner as contracts-only — see [fr018_m1_discovery_contracts.md](fr018_m1_discovery_contracts.md)  
**Date:** 2026-08-07  
**Phase:** Horizon 1B (lead FR)  
**Preceding:** Horizon 1A complete/frozen (FR-008–FR-017); roadmap remap
[changelog § 1.115](../11_changelog.md); FR-008 acquisition boundary
([acceptance](fr008_workflow_orchestration.md); [ADR-003](../adr/003_application_workflow_orchestration.md));
FR-009 Opportunity SoT / duplicates ([acceptance](fr009_opportunity_review_queue.md);
[ADR-004](../adr/004_opportunity_review_boundary.md)); FR-016 Job Discovery
compatibility placeholder ([fr016_m0 §23](fr016_m0_engineering_spike.md))  
**Scope (M0):** Document-only architecture spike. **No production code.**  
**Does not begin (M0):** M1 adapters, live board fetches, scheduled jobs,
Opportunity mutation, Playwright, FR-008–017 redesign, Masterclass generation.

**Owner direction accepted for this spike:**

1. Mission is **lawful opportunity inflow** into the frozen Horizon 1A pipeline.
2. **Discovery Ingress** is the approved coordination direction — pressure-tested here.
3. Prefer APIs / feeds / email / exports / URLs over browser automation; **no scrape theatre**.

---

## 1. Executive summary

Horizon 1A delivered a complete application OS. Acquisition today remains
**paste** and **local export** only. The largest remaining product bottleneck is
getting suitable advertisements into that path with less manual effort.

**Finding:** The frozen `AcquisitionAdapter` → `ApplicationWorkflowRunner.start`
→ persist-before-review path is sufficient. FR-018 must **extend** that boundary,
not redesign FR-008–017.

**Finding:** **Discovery Ingress** is valid **only** as a thin coordinator:
resolve Opportunity Sources → instantiate adapters → invoke the existing runner.
It must not become a second orchestration engine, Opportunity store, or business
service.

**Finding:** Among lawful first milestones, **owner-supplied URL acquisition** is
the best M1. Email alerts likely deliver higher *volume* later but need auth,
MIME fixtures, and parser design that M0 cannot safely start in code. Official
public APIs for major AU boards are generally unavailable. Playwright remains
**last resort / NO-GO for M1**.

**M0 recommendation:** **GO to M1 under narrow scope** (URL adapter + thin owner
CLI + fixture tests + ingress idempotency check against existing Opportunities).
**NO-GO** on scrape-first, Playwright-default, parallel discovery catalogues, and
agent discovery tools.

---

## 2. Engineering problem (restated)

How do we **lawfully discover and acquire** suitable job advertisements into CIC
such that:

1. each posting enters with **explicit provenance**;
2. handoff uses the **frozen** FR-008/009 path without reopening Horizon 1A;
3. duplicates remain **linked, never merged** via existing identity facets;
4. the owner still **decides** apply / skip / defer;
5. we do not invent crawlers, a second SoT, or automation theatre?

This is **ingress engineering**, not application automation.

---

## 3. Dual-value and commercial honesty

| Test | Result for narrow FR-018 (URL-first M1) |
|------|----------------------------------------|
| Improve interview/offer odds? | **Yes, indirect** — more suitable Opportunities enter review/submit |
| Reduce job-search effort? | **Yes** — removes paste/export for URL-available ads |
| Required infrastructure? | Modest — one adapter + thin ingress + CLI |

**Near-term commercial value: high** relative to Recruiter Intelligence first
(already remapped).  
**Learning value: high** if architecture stays adapter-based and compliance-aware.

If M1 cannot fetch owner URLs fail-closed with fixtures, dual-value collapses —
fail closed rather than scrape.

---

## 4. Current architecture inventory (reuse proof)

### 4.1 Ownership matrix (normative)

| Concern | Owner FR | FR-018 role |
|---------|----------|-------------|
| Thin workflow runner, checkpoints, retries | FR-008 | **Reuse** — call `start(adapter)` only |
| `AcquisitionAdapter` / `AcquisitionResult` | FR-008 | **Extend** with new adapter implementations |
| Opportunity SoT, review queue, ranking | FR-009 | **Reuse** — no second catalogue |
| Identity facets / duplicate detection | FR-009 | **Reuse** — improve facets via `source_url` |
| Truth / BOPA / DOS / derive-only eval | FR-014–017 | **None** — do not reopen |
| Discovery Ingress (thin) | **FR-018 (proposed)** | Resolve sources → adapters → runner |
| Scrape farms / crawlers | — | **Out of scope** |

### 4.2 Existing contracts (do not widen for batch)

From `career_intelligence.orchestration.acquisition`:

| Type | Role |
|------|------|
| `AcquisitionResult` | One posting + provenance (`source_kind`, `raw_content`, `posting`, optional `source_identifier` / `source_url` / title / company / `warnings` / `acquired_at`) |
| `AcquisitionAdapter` | Protocol: `source_kind` + `acquire() -> AcquisitionResult` |
| `AcquisitionError` | Fail-closed acquisition failure |

Implemented today: `PasteAcquisitionAdapter`, `LocalFileAcquisitionAdapter`.  
Reserved literals (unimplemented): `url`, `api`, `email`, `saved_search`,
`playwright`, `other`.

Runner: `ApplicationWorkflowRunner.start(source: AcquisitionAdapter | PasteJobInput)`
— does **not** branch on `source_kind`.

### 4.3 Handoff sequence (frozen)

```text
acquire → validate_normalise → analyse → assess → match → strategy
  → persist (decision = None) → owner_review → record_decision
```

Matches FR-016 M0 §23 future Job Discovery compatibility placeholder.

---

## 5. Opportunity Source vs Opportunity (domain)

| Concept | Durable? | Role |
|---------|----------|------|
| **Opportunity** | **Yes** — `data/opportunities/` SoT | Analysed candidate; review metadata; pipeline |
| **OpportunitySource** | **No** — transient ingress metadata | Channel + locator + auth posture for one acquire attempt |
| Discovery run / audit (optional later) | Recovery only | Must not catalogue business Opportunities |

**Why Opportunity remains the only durable business record**

1. ADR-004: single SoT; review queue and duplicates are **derived**.
2. A “seen jobs” discovery store would recreate the pre–FR-009 checkpoint-as-catalogue
   failure mode.
3. Skip/defer/apply auditability requires Opportunities created through the analysis
   path (or an explicit owner-approved exception — none proposed here).

**OpportunitySource** may exist as a typed value object or CLI argument shape in M1;
it must dissolve into `AcquisitionResult` provenance once acquire succeeds.

**Interview takeaway:** Ingress metadata is ephemeral; business truth is the
Opportunity aggregate.

---

## 6. Discovery Ingress — pressure test

### 6.1 Approved responsibility (normative)

Discovery Ingress **may only**:

1. Resolve Opportunity Sources (locators → adapter instances).
2. Instantiate the correct `AcquisitionAdapter`.
3. Invoke existing `ApplicationWorkflowRunner.start(adapter)` (or equivalent public
   entry that already accepts adapters).
4. Optionally **pre-check** existing Opportunities for definite identity matches
   (idempotency warn/skip) — read-only against Opportunity service.
5. Surface warnings / counts to the owner CLI.

### 6.2 Forbidden responsibilities (normative NO-GO)

Discovery Ingress **must not**:

| Anti-pattern | Why rejected |
|--------------|--------------|
| Second workflow / orchestration engine | Reopens ADR-003; duplicates FR-008 |
| Persist Opportunities itself | Bypasses analyse/assess/strategy trust |
| Own a durable “candidate jobs” SoT | Second catalogue; ADR-004 violation |
| Rank, assess, package, truth-validate | Owned by frozen FRs |
| Submit, pipeline advance, recruiter contact | Human gates + later FRs |
| Batch-mutate ToolPolicy / agent allow-lists | ADR-007/008 forbid discovery as agent tools |

### 6.3 Alternatives considered

| Alternative | Verdict | Why |
|-------------|---------|-----|
| A. Adapters only; no ingress type | Weaker | CLI would re-implement resolution/idempotency ad hoc |
| B. Fat Discovery service (analyse inside) | **Reject** | Redesigns Horizon 1A |
| C. Multi-agent Acquisition Specialist (MVP) | **Reject** | Theatre; FR-016 placeholder only |
| D. **Thin Discovery Ingress** | **Accept** | Matches adapter isolation + reuse |

**Principle demonstrated:** Orchestration coordinates; adapters channel; services
execute — Ingress is coordination only.

**Interview takeaway:** “Thin ingress, fat reuse” — the smallest new component that
preserves a frozen pipeline.

---

## 7. Acquisition mechanism comparison

Representative mechanisms (owner workflow is one validation example, not the only
design input).

| Mechanism | Complexity | Stability | Maintenance | Lawfulness | Platform dependence | Owner UX | Commercial value | Learning value | M0 posture |
|-----------|------------|-----------|-------------|------------|---------------------|----------|------------------|----------------|------------|
| Official APIs | Low–med if exist | High | Low | Best | Provider | Excellent | High | Med | Investigate; adopt if real |
| Structured feeds / RSS | Low–med | Med | Low | Usually OK | Provider | Good | Med–high | Med | M2+ candidate |
| Email alerts | Med | Med | Med–high (parsers) | Owner mailbox | Provider templates | Strong volume | **High** | High | **M2 candidate** |
| Manual URLs | Low | High | Low | Owner-supplied fetch | Board HTML risk | Immediate | **High for M1** | High (facets) | **M1** |
| Export files | Low | High | Low | High | None | Manual | Med (exists) | Low | Shipped FR-008 |
| Supported integrations | Unknown | Unknown | Med | Depends | High | Good | Unknown | Med | Defer unless found |
| Browser automation | High | Brittle | **High** | ToS / anti-bot risk | Extreme | Fragile | False economy | Low if scrape story | **Last resort** |

### 7.1 URL-first hypothesis — pressure test

**Hypothesis:** URL acquisition should be M1.

**Challenge — email-first?**  
Email alerts often deliver the highest *passive* volume for SEEK/LinkedIn-style
searches. However M1 email requires: mailbox access posture, MIME/HTML fixtures,
template drift handling, and security review. That is a larger first slice and
risks shipping a brittle parser as the “hello world.”

**Challenge — API-first?**  
Desk review (spike-level): major AU/consumer job boards used in this search do
**not** expose a simple owner-usable public “list suitable AI jobs” API for CIC.
Building against unavailable APIs delays value.

**Challenge — export-only improvements?**  
Already shipped; marginal dual-value vs URL.

**Challenge — Playwright-first?**  
Technically tempting; commercially and legally weak; contradicts principles
failure mode #2 and FR-008 avoid-list.

**Verdict:** **Confirm URL-first for M1.** Email/feeds are the primary M2
hypothesis after URL proves handoff + identity facets. Playwright remains
out of M1–M2 unless a later spike revises with explicit owner approval.

**Why URL wins as first milestone**

1. Lawful owner-supplied locator.
2. Immediately improves `derive_source_facets` (Seek/LinkedIn/Indeed IDs).
3. Reuses reserved `source_kind="url"`.
4. Smallest fail-closed adapter (fetch → text → `AcquisitionResult`).
5. Teaches provenance + idempotency without inbox complexity.

---

## 8. Provenance design (validated)

### 8.1 Required fields on every successful acquire

| Field | Required | Notes |
|-------|----------|-------|
| `source_kind` | Yes | e.g. `url` for M1 |
| `raw_content` | Yes | Non-empty; fail closed otherwise |
| `posting` | Yes | Typed `JobPosting` |
| `source_identifier` | Strongly required for M1 | Canonical URL string or stable hash of URL |
| `source_url` | Strongly required for M1 | Feeds identity facets |
| `acquired_at` | Yes | Ingress timestamp |
| `warnings` | As needed | Soft issues; not silent success on empty body |
| title / company | Optional | Prefer extracted/grounded; never invent |

### 8.2 Duplicate detection compatibility

Existing FR-009 behaviour (reuse):

- Definite: same `canonical_url` / `source_url` / (`platform` + `platform_job_id`)
- Probable / possible: company/title/location/fingerprint clusters
- Fingerprint alone is **not** a merge key (ADR-004)

URL-first M1 maximises definite matches. Paste-without-URL remains weaker — not
the FR-018 focus.

### 8.3 Idempotent acquisition behaviour (normative for M1+)

Before `runner.start` for a URL (or other locator with definite facets):

1. Query Opportunity service for definite identity match.
2. If match: **warn/skip** (or owner `--force` only if later approved) — **never
   merge/delete**.
3. If no match: proceed through full FR-008/009 path.
4. Post-persist: existing duplicate detection may still propose probable groups;
   owner confirms.

Ingress idempotency is **advisory skip**, not silent data destruction.

---

## 9. Pipeline integration (no Horizon 1A redesign)

```text
OpportunitySource (transient)
  → Discovery Ingress
  → AcquisitionAdapter.acquire() → AcquisitionResult
  → ApplicationWorkflowRunner.start(adapter)
  → frozen PRE_APPROVAL_SEQUENCE
  → Opportunity SoT + derived review queue
```

| Frozen FR | Change required? |
|-----------|------------------|
| FR-008 runner / checkpoints / retries | **No** |
| FR-009 SoT / queue / dupes / rank | **No** (read for idempotency) |
| FR-014 truth | **No** |
| FR-015 BOPA | **No** — no discovery tools |
| FR-016 DOS/OBS | **No** — placeholder hand-in remains future |
| FR-017 eval | **No** |

Optional later ADR (M1+): record Discovery Ingress boundary decisions if they
exceed what ADR-003 already implies for adapters.

---

## 10. Human approval boundaries

| Action | Allowed in FR-018 |
|--------|-------------------|
| Owner supplies URL / later email export | Yes |
| Fetch content for owner-supplied locator | Yes (M1+) |
| Create Opportunity via existing persist-before-review | Yes |
| Owner apply / skip / defer | Required (unchanged) |
| Silent submit / outreach / pipeline advance | **No** |
| Agent-initiated mutating discovery | **No** without new ADR + owner acceptance |

---

## 11. Risks and mitigations

| Risk class | Risk | Mitigation |
|------------|------|------------|
| Technical | HTML layout drift on URL fetch | Extract visible text conservatively; warnings; fixtures; fail closed on empty |
| Technical | Dual SoT temptation | Normative: no discovery catalogue |
| Maintenance | Email parser sprawl (M2) | Fixture corpus; narrow providers; defer if unstable |
| Platform | Rate limits | Owner-paced CLI first; no aggressive schedulers in M1 |
| ToS | Treating fetch as scrape farm | Owner-supplied URLs only in M1; no mass crawl; document posture |
| Owner UX | Fetch fails on JS-heavy pages | Warning + fallback to paste/export; Playwright only if later GO |
| Commercial | Building theatre instead of inflow | Dual-value gate; URL M1 ships real path |
| Portfolio | “We scraped LinkedIn” narrative | Refuse; tell adapter/compliance story |

---

## 12. Recommended scope (post-GO)

### In scope (FR-018)

- Thin Discovery Ingress (resolve → adapter → runner)
- New lawful adapters starting with **URL**
- Provenance-complete results
- Ingress idempotency against Opportunity identity
- Thin owner CLI
- Fixture-based automated tests (no network in CI)

### Out of scope / NO-GO slices

- Scrape-first / uncontrolled crawlers / access-control bypass
- Playwright as M1 default
- Parallel Opportunity catalogue
- Redesign of FR-008–017
- Auto apply / submit / recruiter messaging
- Discovery on BOPA/DOS allow-lists
- Dashboards; Academy artefacts during engineering

### Deferred

- Email alert ingress (M2 hypothesis)
- Feeds / saved-search (M2–M3)
- Official APIs if/when available
- Scheduling / multi-URL batch UX polish (M3)
- Playwright last-resort spike (only with owner + revised GO)

### Proposed milestones (planning; M1 not started)

| Milestone | Intent |
|-----------|--------|
| **M0** | This spike — **Complete** pending owner accept |
| **M1** | `UrlAcquisitionAdapter` + thin CLI + fixtures + idempotency pre-check |
| **M2** | Email and/or feed ingress (M0-ranked) |
| **M3** | Batch/ops hardening |
| **M4** | Evaluation / acceptance freeze |

---

## 13. Testing posture (for M1 planning; not executed in M0)

- Deterministic fixtures; **no network in CI**
- Fake HTTP / saved HTML for URL adapter unit tests
- Functional: adapter → runner → identity facets on fixtures
- Manual owner validation on real saved URLs after M1

---

## 14. Learning and interview value

### Major decisions (teachable)

**D1 — Thin Discovery Ingress**  
- **Why:** Coordinate without redesigning the runner.  
- **Alternative:** Fat discovery orchestrator.  
- **Rejected:** Reopens frozen Horizon 1A.  
- **Principle:** Reuse before redesign; adapters channel.  
- **Interview:** Smallest boundary that preserves SoT ownership.

**D2 — Keep `AcquisitionAdapter` one-posting**  
- **Why:** Runner is source-agnostic; batch belongs at ingress.  
- **Alternative:** Widen Protocol to `acquire_many`.  
- **Rejected:** Forces runner/API churn.  
- **Principle:** Deterministic first; narrow interfaces.  
- **Interview:** Don’t break frozen contracts for convenience.

**D3 — URL-first M1**  
- **Why:** Lawful, facet-rich, smallest slice.  
- **Alternative:** Email-first or Playwright-first.  
- **Rejected (for M1):** Complexity / ToS.  
- **Principle:** Validate first; no scrape theatre.  
- **Interview:** Compliance-aware integration beats clever scraping.

**D4 — Opportunity-only SoT**  
- **Why:** ADR-004 lesson.  
- **Alternative:** Discovery candidate DB.  
- **Rejected:** Dual catalogue.  
- **Principle:** One system of record.  
- **Interview:** Derived views over durable records, not shadow stores.

### Academy evidence left by this spike

Alternatives, invariants, dual-value honesty, GO/NO-GO table, milestone non-goals,
provenance/idempotency rules — sufficient for later Acceptance → Masterclass →
Interview Brief/Deck after freeze. **No Academy artefacts generated now.**

---

## 15. Go / no-go table

| Slice | Verdict |
|-------|---------|
| Thin Discovery Ingress (resolve → adapter → runner only) | **GO** |
| Keep `AcquisitionAdapter` narrow (one posting) | **GO** |
| Opportunity as sole durable SoT; Source transient | **GO** |
| URL-first M1 | **GO** |
| Email/feeds as M2+ | **GO (deferred)** |
| Official APIs if unavailable | **DEFER** until real API exists |
| Playwright / scrape-first | **NO-GO** for M1–M2 default |
| Parallel discovery Opportunity catalogue | **NO-GO** |
| Redesign FR-008–017 | **NO-GO** |
| Agent discovery tools on BOPA/DOS | **NO-GO** |
| Auto apply / outreach | **NO-GO** |
| M1 implementation in this spike | **NO-GO** (docs only) |

---

## 16. M0 recommendation

**GO to M1 under narrow scope.**

1. Owner accepts this M0 spike.
2. M1 plans/implements **URL acquisition** + thin Discovery Ingress + CLI +
   fixture tests + idempotency pre-check.
3. Do **not** begin Playwright, email, or APIs in M1 unless owner revises to
   **GO WITH REVISED SCOPE**.
4. Recruiter Intelligence remains **FR-019**.

**Alternate owner replies**

| Choice | Meaning |
|--------|---------|
| Accept M0 as written | Unlock M1 planning/implementation under URL-first |
| Accept with revisions | List changes (e.g. email-first) |
| Defer FR-018 | Capacity on live applications; record in changelog |
| Reject | Architecture not justified; close or redesign spike |

**No M1 work begins without an explicit choice above.**

---

## 17. M0 definition of done

- [x] Engineering problem restated
- [x] Dual-value honesty recorded
- [x] Architecture inventory / reuse matrix
- [x] Discovery Ingress pressure-tested (allowed vs forbidden)
- [x] Mechanism comparison across representative sources
- [x] URL-first hypothesis challenged and confirmed
- [x] Opportunity vs OpportunitySource clarified
- [x] Provenance + dedup + idempotency specified
- [x] Pipeline integration without Horizon 1A redesign
- [x] Risks + mitigations
- [x] Learning / interview decision records
- [x] Explicit GO / NO-GO table
- [x] Owner next-step block
- [x] No production code / adapters / runtime changes

---

## 18. Final repository status (at M0 close)

| Item | Status |
|------|--------|
| Horizon 1A FR-008–FR-017 | Frozen / unchanged |
| FR-018 M0 spike | **Complete** — **GO to M1 under narrow scope** |
| M1 URL adapter / CLI | **Not started** — awaits owner acceptance |
| Production acquisition beyond paste/export | Unchanged |

**M0 COMPLETE**  
**GO to M1 under narrow scope**  
**FR-018 READY FOR M1 PLANNING (IF OWNER ACCEPTS)**
