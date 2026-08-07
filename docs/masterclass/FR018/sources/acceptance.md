<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/eval/fr018_opportunity_discovery_acquisition.md
Mode: full-file snapshot
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

# FR-018 — Opportunity Discovery & Acquisition

**Status:** **Complete / Frozen / Accepted**  
**Date:** 2026-08-07  
**Documentation close-out:** 2026-08-07  
**Recommendation:** **ACCEPT AND FREEZE — FR-018 COMPLETE**  
**Binding product posture:** **thin Discovery Ingress + channel adapters into frozen Horizon 1A**  
**Engineering Learning Academy:** **Ready** — canonical engineering record =
this report; attachable package =
[masterclass/FR018/](../masterclass/FR018/) (`README.md`, `MANIFEST.md`, regenerable
`sources/`)  
**Next:** **FR-019 Recruiter Intelligence** on owner request. Do not reopen
Horizon 1A. Authenticated browsers / Easy Apply / recruiter workflows are later FRs.

**ADR:** [ADR-010](../adr/010_opportunity_discovery_ingress.md) (Accepted — M1–M4 close-out)

**Milestones (historical records):**
[M0](fr018_m0_engineering_spike.md) (Accepted),
[M1](fr018_m1_discovery_contracts.md) (Accepted),
[M2](fr018_m2_url_discovery_ingress.md) (Accepted — GO WITH REVISED SCOPE),
[M3](fr018_m3_production_hardening.md) (Accepted — GO WITH REVISED SCOPE),
[M4](fr018_m4_email_job_alert_acquisition.md) (Accepted — live validation;
this freeze).

This document is the **canonical engineering record** for FR-018. Milestone reports
remain historical; do not reopen exit criteria without owner request.

---

## 1. Executive Summary

FR-018 delivers the **Opportunity Acquisition Framework** for Horizon 1B:

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

| Channel | Status |
|---------|--------|
| Owner URL (`cic opportunity discover`) | **Production** — SEEK primary; LinkedIn/Indeed attempt/fail-closed |
| Owner-saved job-alert `.eml` (`cic opportunity discover-email`) | **Production** — SEEK / LinkedIn / Indeed alerts |
| Email → URL enrichment | **Accepted** — card-only alerts reuse `UrlAcquisitionAdapter` |
| IMAP / Playwright / recruiter CRM | **Out of scope** |

**Live owner validation (LinkedIn alert):** `acquired=6 failed=0`; re-run without
`--force` → `skipped=6` (definite identity). Full Job Analysis, Assessment,
Portfolio Match, and Application Strategy succeeded on enriched ads.

**Horizon 1A unchanged.** No second orchestrator, Opportunity store, or acquisition
Protocol redesign.

---

## 2. Engineering Summary

### Problem

Horizon 1A can prepare and track applications, but inflow was mostly paste/export.
FR-018 scales **lawful** discovery into that loop.

### Solution shape

- **Thin ingress** (ADR-010) — resolve → adapter → existing runner; optional
  definite-identity skip.
- **Reuse FR-008** `AcquisitionAdapter` / `AcquisitionResult`.
- **Channels as adapters** under one FR (Hybrid / Option C), not one mega-FR per board.

### Critical refinement (acceptance)

Initial M4 used alert-body text as the JobPosting. Live LinkedIn digests are
**discovery cards** (~500 chars: title/company/location). That produced hollow
JobAnalysis and flaky Assessment (`Invalid JSON`).

**Accepted design:** email discovers the job URL; when the alert body is card-only,
**enrich via existing `UrlAcquisitionAdapter`** (fail-soft). Provenance remains
`source_kind=email`. No parallel acquisition stack.

---

## 3. Architecture

| Concern | Owner | FR-018 role |
|---------|-------|-------------|
| Workflow / analyse / assess / strategy | FR-008–FR-011 | Unchanged |
| Opportunity SoT / duplicates | FR-009 | Definite-identity skip only |
| Thin Discovery Ingress | **FR-018** | Coordinate |
| URL acquire | **FR-018** | `UrlAcquisitionAdapter` |
| Email discover + optional URL enrich | **FR-018** | `EmailAcquisitionAdapter` |
| Recruiter / outreach / Easy Apply | FR-019+ | Out of scope |

**Invariant:** Ingress must not rank, assess, persist Opportunities itself, generate
documents, submit, or confirm duplicates.

**Package:** `career_intelligence.discovery`  
**CLI:** `cic opportunity discover` / `discover-email`

---

## 4. Final implementation

| Component | Role |
|-----------|------|
| `OpportunitySource` | Transient `url` or `email` locator |
| `ThinDiscoveryIngress` | Protocol implementation |
| `UrlAcquisitionAdapter` | HTTP fetch + HTML extract |
| `EmailAcquisitionAdapter` | `.eml#job=N` parse; optional URL enrich |
| `parse_job_alert_email` | Allow-listed senders; SEEK / LinkedIn (`/jobs/view` + `/comm/jobs/view`) / Indeed |
| Provenance asserts | Fail-closed URL and email |
| TLS | `truststore.SSLContext` for live fetch (M3) |

**Email enrichment rule:** Prefer URL body when substantially longer **or** when the
email lacks JD signals and the URL body has them. Offline fixtures skip enrichment.

---

## 5. Live validation evidence

| Run | Result |
|-----|--------|
| `cic opportunity discover-email linkedin_alert.eml --force` | **acquired=6 skipped=0 failed=0** |
| Enrichment | Full ads via URL adapter (≈3.2k–5.5k chars) |
| Pipeline | JobAnalysis + Assessment + Portfolio Match + Strategy → Opportunities |
| Re-run without `--force` | **acquired=0 skipped=6 failed=0** |
| Skip reason | Definite identity match on email job URL facets |

Unit coverage: `tests/unit/discovery/` (email enrich + ingress regressions).

---

## 6. Before vs After

| | Initial M4 (pre-acceptance) | Accepted |
|--|------------------------------|----------|
| Email content | Alert card as JobPosting | Card discovers URL; URL adapter supplies JD when possible |
| LinkedIn live | Parse OK; thin analyse/assess fail/flake | Full pipeline on enriched ads |
| Architecture | Email-only body path | Reuse canonical URL acquire |
| Duplicates | Planned definite skip | Confirmed live (`skipped=6`) |

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| LinkedIn/Indeed URL fetch intermittent | Fail-soft to card; document limits (M3); paste remains available |
| Card-only when enrich fails | Honest insufficient strategy / owner paste |
| Anti-bot / auth walls | No Playwright in FR-018; later FR if needed |
| Treating email as authoritative JD | Explicit lesson — email is discovery |

---

## 8. Lessons Learned

1. **Passing unit tests did not demonstrate product readiness** — live owner
   validation exposed the card-only gap.
2. **Email alerts are a discovery mechanism**, not an authoritative job description.
3. **Correct fix was reuse of URL acquisition**, not deeper email HTML parsing.
4. **Live validation improved design while simplifying architecture** (one acquire path).
5. **Live validation is mandatory for external integrations.**

---

## 9. Recommendation

**ACCEPT AND FREEZE FR-018.**

No further implementation for this FR. Future work (authenticated browser, Easy
Apply, recruiter intelligence) belongs to **FR-019+**.

---

## 10. Final acceptance decision

| Decision | Value |
|----------|-------|
| FR-018 | **ACCEPTED** |
| Freeze | **FROZEN** |
| Horizon 1A | **Unchanged / not reopened** |
| Academy package | [masterclass/FR018/](../masterclass/FR018/) |
| Next FR | **FR-019 Recruiter Intelligence** (owner request) |

**FR-018 ACCEPTED. FR-018 FROZEN. READY FOR FR-019.**
