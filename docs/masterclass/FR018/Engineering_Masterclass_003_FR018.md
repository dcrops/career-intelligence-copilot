# Engineering Masterclass 003

## Career Intelligence Copilot — FR-018 Opportunity Discovery & Acquisition

**Subtitle:** Thin Ingress, Email as Discovery, and Canonical URL Enrichment  
**Edition:** Engineering Learning Academy — Lean Edition  
**Status:** Complete / Frozen / Accepted  
**Audience:** Experienced software engineers preparing for technical interviews  
**Source package:** `docs/masterclass/FR018/` (educational packaging; repository SoT remains authoritative)

---

### Executive Summary

FR-018 answers a practical scaling question: once a frozen application pipeline can analyse, assess, prepare, and track opportunities, how do you increase **lawful job inflow** without rebuilding orchestration?

The accepted answer is a **thin Discovery Ingress** plus **channel adapters**. Owner URLs and owner-saved job-alert `.eml` files become transient `OpportunitySource` values. Ingress resolves the source, calls an `AcquisitionAdapter`, and hands a normal `AcquisitionResult` to the existing Horizon 1A runner. Opportunity remains the only durable business record. Ingress does not rank, assess, persist Opportunities itself, generate documents, or submit applications.

Live LinkedIn validation forced one critical refinement. Job-alert emails look like content sources, but they often contain only **discovery cards** (~500 characters: title, company, location). Feeding that text into analysis produced hollow JobAnalysis and flaky Assessment. The accepted fix was not deeper email HTML parsing. It was **reuse of the existing URL acquisition path**: email discovers the job URL; the URL adapter fetches the full advertisement when possible; provenance stays `source_kind=email`.

If you can explain FR-018 well in an interview, you can explain how mature systems extend frozen pipelines with thin ingress, treat external digests as discovery rather than authority, and let live validation simplify architecture instead of expanding it.

---

### 1. The Engineering Problem

Horizon 1A already owned the application loop: acquire → analyse → assess → portfolio → strategy → Opportunity store → preparation → submission assistance → pipeline tracking. What it lacked was scalable, lawful **inflow**. Paste and export worked, but volume discovery did not.

An owner (or interviewer) needed answers to:

1. How do you add SEEK / LinkedIn / Indeed inflow without a second orchestrator?
2. Where does discovery stop and frozen acquisition start?
3. What is durable — the discovery locator, or the Opportunity?
4. When an email alert looks like a job description but is not one, what do you do?
5. How do you avoid inventing a parallel “seen jobs” catalogue beside FR-009?

FR-018’s real problem statement is therefore:

> Scale lawful opportunity discovery into a frozen Horizon 1A pipeline — without reopening orchestration, without a second Opportunity store, and without treating discovery cards as authoritative job descriptions.

---

### 2. Why Previous Approaches Were Insufficient

#### 2.1 Fat discovery orchestrator

Putting analyse / assess / ranking inside discovery would reopen FR-008. Ingress would become a second workflow engine with competing authority. Rejected.

#### 2.2 One mega-FR per job board

Building separate SEEK, LinkedIn, and Indeed products multiplies surface area and hides the shared pattern: **channel adapter → acquisition contract → existing runner**. FR-018 chose one framework with adapters (Hybrid / Option C).

#### 2.3 Parallel “seen jobs” store

A second catalogue for discovery identity would violate ADR-004. Opportunity is the system of record. Definite-identity skip may *read* Opportunities; it must not invent a twin store.

#### 2.4 Treat email alert bodies as the JobPosting

The initial M4 path was:

```text
Email → parse card → Horizon 1A
```

Unit tests passed. Live LinkedIn digests exposed the product gap: cards are not JDs. Hollow analysis and intermittent Assessment failure followed. Extending email parse depth would have optimized the wrong artefact.

#### 2.5 Authenticated browser / Easy Apply inside discovery

Playwright walls, authenticated sessions, and Easy Apply are later product decisions. Stuffing them into FR-018 would have delayed freeze and blurred Horizon 1B recruiter work (FR-019+).

---

### 3. The Chosen Architecture

```text
OpportunitySource (url | email .eml#job=N)
        ↓
ThinDiscoveryIngress (coordinate only)
        ↓
AcquisitionAdapter (URL | Email → optional URL enrich)
        ↓
ApplicationWorkflowRunner (frozen Horizon 1A)
        ↓
Opportunity (FR-009 SoT)
```

#### 3.1 Ownership matrix

| Concern | Owner | FR-018 role |
|---------|-------|-------------|
| Workflow / analyse / assess / strategy | FR-008–FR-011 | Unchanged |
| Opportunity SoT / duplicates | FR-009 | Definite-identity skip only |
| Thin Discovery Ingress | **FR-018** | Coordinate |
| URL acquire | **FR-018** | URL adapter |
| Email discover + optional URL enrich | **FR-018** | Email adapter |
| Recruiter / outreach / Easy Apply | FR-019+ | Out of scope |

#### 3.2 Thin ingress invariants

Ingress may resolve sources, instantiate adapters, invoke the existing runner, and optionally skip on definite identity. It must not rank, assess, own Opportunity persistence, generate documents, submit, or confirm duplicates for the owner.

#### 3.3 Channels as adapters

- **URL path** — production for SEEK; LinkedIn/Indeed attempt/fail-closed; paste remains fallback.
- **Email path** — owner-saved `.eml` digests; allow-listed senders; one source per job URL fragment (`path.eml#job=N`).

#### 3.4 Accepted refinement: email discovers; URL acquires

```text
Job alert .eml
  → parse cards + job URLs
  → Email adapter (card text)
  → if card-only / thin: UrlAcquisitionAdapter(job_url)  [fail-soft]
  → AcquisitionResult(source_kind=email, body=enriched JD when available)
  → Horizon 1A
```

No duplicate acquisition architecture. Enrichment reuses the canonical URL path. Offline fixtures skip live enrich. Fail-soft keeps the card if fetch fails — honesty over theatre.

#### 3.5 What was explicitly not built

No IMAP client. No Playwright discovery crawler. No second Opportunity store. No fat ingress. No Easy Apply. No recruiter CRM. No Horizon 1A reopen.

#### 3.6 Runtime Example

One conceptual discovery flow (diagram seed):

```text
Owner supplies URL or job-alert .eml
        ↓
Thin ingress resolves OpportunitySource
        ↓
Channel adapter acquires (email may enrich via URL fetch)
        ↓
Frozen Horizon 1A runner produces Opportunity
        ↓
Re-ingest skips on definite identity — no twin catalogue
```

---

### 4. Engineering Principles

#### 4.1 Thin ingress, frozen pipeline

Extend by coordination, not by cloning orchestration. Authority stays where it was proven.

#### 4.2 Discovery is not authority

Email alerts and board cards discover candidates. The job advertisement (or owner paste) is the content authority for analysis.

#### 4.3 Reuse before deepen

When a card lacks a JD, fetch via the existing URL adapter. Do not invent a second acquire stack or deepen HTML parse theatre.

#### 4.4 One Opportunity system of record

Transient sources are ingress metadata. Durable business state is Opportunity. Definite duplicates are linked/skipped, never silently merged away.

#### 4.5 Fail closed / fail soft with honesty

Unsupported senders and missing job URLs fail closed. Enrichment fails soft to the card. Strategy may honestly report insufficient information rather than invent detail.

#### 4.6 Live validation for external integrations

Board/email integrations are not “done” when fixtures pass. Live owner validation is part of design, not a ceremony after freeze.

---

### Why Employers Care

Employers need engineers who can attach new inflow channels to a frozen core without rewriting the core. This work shows transferable judgment: keep ingress thin, refuse dual sources of truth, treat third-party digests as discovery signals, and prefer reuse of a proven acquisition path over expanding parsers. Live validation that *simplifies* architecture is a senior signal — product readiness over green unit suites.

---

### 5. Validation

#### Validation Summary

| Item | Result |
|------|--------|
| Major outcome | Live LinkedIn alert → full Horizon 1A on enriched ads |
| Live counts | **acquired=6 failed=0**; re-run **skipped=6 failed=0** |
| Recommendation | **ACCEPT AND FREEZE** — thin ingress + URL enrich |
| Constraints | No IMAP/Playwright/Easy Apply; Horizon 1A unchanged; email provenance retained |

#### 5.1 Live owner validation (LinkedIn)

Real `.eml` digest:

- six jobs parsed
- email → URL enrichment
- existing URL adapter retrieved full advertisements
- Job Analysis, Assessment, Portfolio Match, Application Strategy succeeded
- six Opportunities created

Second execution without force:

- acquired=0, skipped=6, failed=0
- reason: definite identity match on email job URL facets

#### 5.2 Unit and fixture evidence

Discovery unit coverage locks parse, enrich rules, ingress coordination, and provenance asserts. Fixtures remain necessary — they are not sufficient for board/email readiness.

#### 5.3 Before vs after (the teaching pivot)

| | Initial M4 | Accepted |
|--|------------|----------|
| Email content | Card as JobPosting | Card discovers URL; URL supplies JD when possible |
| LinkedIn live | Thin analyse / flaky assess | Full pipeline on enriched ads |
| Architecture | Email-only body path | Reuse canonical URL acquire |

#### 5.4 What “validated” means here

Validated means the owner path works on real alert mail with honest skip semantics — not that every board fetch is guaranteed forever. LinkedIn/Indeed URL fetch may still fail closed; paste remains available.

---

### 6. Trade-offs

#### Accepted

| Choice | Why it was worth it |
|--------|---------------------|
| Thin ingress over fat discovery | Protects frozen Horizon 1A authority |
| Adapters under one FR | Shared framework; board-specific parsers stay local |
| Email → URL enrich | Fixes product gap without second acquire architecture |
| Owner-supplied `.eml` (no IMAP) | Defers mailbox auth; keeps M4 bounded |
| Definite-identity skip | Idempotent re-ingest without dual SoT |

#### Deferred

Authenticated browsers, Easy Apply, IMAP sync, recruiter workflows, and broader anti-bot strategies — later FRs when justified.

#### Out of scope

Recruiter CRM, outreach automation, Playwright as primary discovery, second Opportunity catalogue, reopening FR-008–FR-017 exit criteria.

#### Honest product assessment

| Question | Answer |
|----------|--------|
| Improves lawful inflow into 1A? | Yes |
| Treats email as authoritative JD? | No — discovery only |
| Required a new acquisition stack? | No — reused URL acquire |
| Ready for FR-019? | Yes, on owner request |

---

### 7. Interview Preparation

**Q: What problem did FR-018 solve?**  
A: Scaling lawful opportunity discovery into a frozen application pipeline without a second orchestrator or Opportunity store.

**Q: What is thin Discovery Ingress?**  
A: A coordinator that resolves sources, calls acquisition adapters, and invokes the existing runner. It does not rank, assess, persist Opportunities itself, generate documents, or submit.

**Q: Why not put analysis inside discovery?**  
A: That reopens the frozen workflow boundary. Discovery should hand off a normal acquisition result, not re-implement Horizon 1A.

**Q: What went wrong with the first email design?**  
A: Unit tests passed while treating alert cards as job descriptions. Live LinkedIn digests were ~500-character cards — hollow analysis and flaky assessment followed.

**Q: What is the accepted email architecture?**  
A: Email discovers the job URL; when the body is card-only, enrich via the existing URL acquisition adapter; keep `source_kind=email`; fail soft if fetch fails.

**Q: Why not deepen email HTML parsing instead?**  
A: That optimizes the wrong artefact. The authoritative advertisement is on the job URL. Reuse beats parse theatre.

**Q: How do duplicates work on re-ingest?**  
A: Definite identity on email job URL facets can skip acquisition. Opportunities are not silently merged or deleted; no parallel seen-jobs store.

**Q: SEEK vs LinkedIn/Indeed?**  
A: SEEK URL path is production-primary. LinkedIn/Indeed attempt and may fail closed; owner paste remains a fallback. Email enrich depends on URL fetch success.

**Q: What stayed out of FR-018?**  
A: IMAP, Playwright discovery, Easy Apply, recruiter CRM/outreach — later product FRs.

**Q: What is the main lesson for external integrations?**  
A: Live validation is mandatory. Green fixtures do not prove product readiness when third parties control the payload shape.

---

### 8. Three Engineering Lessons to Remember

1. **Passing unit tests did not demonstrate product readiness.**  
   Real owner validation exposed that LinkedIn alerts were discovery cards, not job descriptions.

2. **Email alerts discover; they are not the authoritative job description.**  
   Treat digests as locators and signals. Acquire the advertisement through the canonical content path.

3. **Live validation improved the design while simplifying the architecture.**  
   The fix was reuse of URL acquisition — not a deeper email parser and not a second acquisition stack.

---

### Closing Frame

FR-018 freezes a posture senior engineers are often asked to defend:

- extend frozen systems with thin ingress, not twin engines  
- keep one durable business record  
- let external formats fail honestly  
- prefer reuse when live evidence shows the content lives elsewhere  
- treat live validation as design input, not ceremonial sign-off  

That is the interview-ready story. Not “we scraped more boards,” but “we scaled lawful discovery into a frozen pipeline — and let production evidence simplify the acquire path.”

### Memorable Closing Statement

**Discovery finds the door; acquisition walks through the one you already built — validate live before you deepen the parser.**

---

*Lean Edition Masterclass — generated for Engineering Learning Academy import (Gamma later). Does not replace the canonical acceptance report or ADR-010.*
