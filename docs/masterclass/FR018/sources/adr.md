<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/adr/010_opportunity_discovery_ingress.md
Mode: full-file snapshot
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Sibling PDF is rendered automatically by the same command (or: python scripts/render_masterclass_pdf.py --package <FR_ID>).
Repository documentation remains the source of truth.
-->

# ADR-010: Opportunity Discovery Ingress Boundary

**Status:** Accepted (FR-018 M1; **FR-018 Complete / Frozen** — M4 live close-out)  
**Date:** 2026-08-07  
**Related:** [ADR-003](003_application_workflow_orchestration.md),
[ADR-004](004_opportunity_review_boundary.md),
[FR-018 acceptance](../eval/fr018_opportunity_discovery_acquisition.md),
[FR-018 M0](../eval/fr018_m0_engineering_spike.md),
[FR-018 M1](../eval/fr018_m1_discovery_contracts.md)

## Context

Horizon 1A is frozen. Acquisition today is paste/export via
`AcquisitionAdapter` into `ApplicationWorkflowRunner`. FR-018 must scale lawful
inflow without redesigning the runner, Opportunity SoT, or FR-009 duplicates.

M0 accepted a **thin Discovery Ingress** and **URL-first** first executable path.
M1 freezes production contracts and authority boundaries before any fetch/CLI.

## Decision

1. **Discovery Ingress is a thin coordinator only.** It may resolve
   `OpportunitySource` values, instantiate `AcquisitionAdapter` implementations,
   invoke existing `ApplicationWorkflowRunner.start`, and optionally read
   Opportunities for definite-identity idempotent skip. It must not rank, assess,
   own persistence, generate documents, submit, or replace FR-009 duplicate
   confirmation.
2. **Opportunity remains the only durable business record.**
   `OpportunitySource` is transient ingress metadata and must never become a
   second catalogue.
3. **Reuse FR-008 acquisition contracts.** `AcquisitionAdapter` /
   `AcquisitionResult` remain the handoff into AcquireNode. FR-018 does not
   widen the adapter Protocol to batch acquire.
4. **URL-first scope for the first executable milestone after M1.** Email, feeds,
   APIs, scheduling, and Playwright remain out of M1 contracts enforcement
   (`DiscoverySourceKind` / M1 allow-list is `url` only).
5. **Provenance for URL path is fail-closed.** URL `AcquisitionResult` values
   must carry `source_kind="url"`, `source_url`, `source_identifier`, and
   `acquired_at` so FR-009 identity facets can derive.

## Consequences

- Positive: Extends frozen Horizon 1A without a second orchestration engine.
- Positive: Clear Academy-ready authority story (ingress vs runner vs SoT).
- Negative: Volume acquisition (email alerts) waits for a later milestone.
- Negative: JS-heavy pages may fail URL fetch later — paste/export remains fallback.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| Fat discovery orchestrator (analyse inside ingress) | Rejected — reopens FR-008 |
| Parallel “seen jobs” store | Rejected — ADR-004 dual SoT |
| Widen `AcquisitionAdapter.acquire_many` | Rejected — runner churn |
| Email-first contracts in M1 | Rejected — larger surface; deferred |
| No ADR (rely on ADR-003 alone) | Rejected — ingress authority needs explicit record |

## Notes

Does not amend ADR-003 runner design or ADR-004 Opportunity SoT. Amends product
sequencing only by naming the FR-018 ingress boundary.

**M2 implementation (2026-08-07):** Executable `ThinDiscoveryIngress` +
`UrlAcquisitionAdapter` delivered under
[eval/fr018_m2_url_discovery_ingress.md](../eval/fr018_m2_url_discovery_ingress.md)
(**GO WITH REVISED SCOPE** — fixture-proven; live board HTTP may fail closed).
Authority boundaries in this ADR remain binding.

**M3 implementation (2026-08-07):** Production hardening —
[eval/fr018_m3_production_hardening.md](../eval/fr018_m3_production_hardening.md)
(**GO WITH REVISED SCOPE**). SEEK live URL path production-ready with OS trust
store TLS (`truststore.SSLContext`). LinkedIn/Indeed remain attempt/fail-closed.
Ingress authority in this ADR unchanged.

**M4 implementation (2026-08-07):** Email job-alert channel —
[eval/fr018_m4_email_job_alert_acquisition.md](../eval/fr018_m4_email_job_alert_acquisition.md)
(**Accepted**). `DiscoverySourceKind` includes `"email"`; owner-supplied
`.eml` digests expand to one acquire per job URL; ingress remains thin; no IMAP /
recruiter CRM. **Live acceptance refinement:** LinkedIn alert bodies are discovery
cards; `EmailAcquisitionAdapter` optionally enriches via existing
`UrlAcquisitionAdapter` (fail-soft; provenance stays `source_kind=email`).
Authority in this ADR unchanged.

**FR close-out (2026-08-07):** FR-018 **Complete / Frozen / Accepted** —
[eval/fr018_opportunity_discovery_acquisition.md](../eval/fr018_opportunity_discovery_acquisition.md).
Academy: [masterclass/FR018/](../masterclass/FR018/). Next: FR-019 on owner request.
