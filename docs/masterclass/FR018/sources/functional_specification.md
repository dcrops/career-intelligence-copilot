<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/04_functional_specification.md
Mode: section snapshot ('## FR-018 Opportunity Discovery & Acquisition' → '## FR-019 Recruiter Intelligence')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

## FR-018 Opportunity Discovery & Acquisition

**Phase:** Horizon 1B (lead)  
**Status:** **Complete / Frozen / Accepted**
([eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md);
[ADR-010](adr/010_opportunity_discovery_ingress.md); Academy
[masterclass/FR018/](masterclass/FR018/))  
*(Inserted 2026-08-07 — changelog § 1.115. M0–M4 + live close-out: § 1.116–1.125.
Extends the FR-008 acquisition adapter boundary additively; does not reopen
FR-008–FR-017. Synonym in older notes: Job Discovery. Architecture: permanent
Opportunity Acquisition Framework — channels as adapters under FR-018.)*

Discover and acquire suitable job advertisements into CIC via lawful source
adapters, with explicit provenance and idempotent handoff into the frozen
FR-008/FR-009 Opportunity path. Owner review before apply remains mandatory.
Prefer APIs, feeds, alerts, exports, and owner URLs over browser automation.

**M0 architecture (accepted):** thin Discovery Ingress
(resolve → `AcquisitionAdapter` → existing `ApplicationWorkflowRunner` only);
Opportunity sole durable SoT; **URL-first** first executable path; email/feeds
later; Playwright last-resort / not near-term.

**M1 delivered:** typed discovery contracts; provenance validators;
DiscoveryIngress Protocol; ADR-010.

**M2 delivered:** `UrlAcquisitionAdapter`, `ThinDiscoveryIngress`,
`cic opportunity discover`; SEEK/LinkedIn/Indeed locator support with offline
fixtures; definite idempotency; fail-closed unsupported/blocked/network. Live
board HTTP may fail — paste/export remain available. No Playwright.

**M3 delivered:** SEEK production-ready URL path; OS trust-store TLS
(`truststore.SSLContext`); LinkedIn/Indeed evidence-based fail-closed (no
Playwright / anti-bot bypass); no new boards.

**M4 delivered (accepted):** Email job-alert channel — owner-saved SEEK / LinkedIn /
Indeed `.eml` → `EmailAcquisitionAdapter` → optional **URL enrich** via existing
`UrlAcquisitionAdapter` when the alert is card-only → ingress → Horizon 1A;
`cic opportunity discover-email`. Digests expand to one Opportunity per job URL.
Email is a **discovery** mechanism; the job URL acquire path remains the
authoritative advertisement source when enrichment succeeds. No IMAP, no
recruiter CRM, no Playwright. Recruiter Intelligence is **FR-019+**.

**Do not reopen** without explicit owner request.

---
