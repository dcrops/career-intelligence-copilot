<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/07_testing_strategy.md
Mode: section snapshot ('### FR-018 coverage (M1–M4 — frozen)' → '**Spike rule:**')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

### FR-018 coverage (M1–M4 — frozen)

FR-018 is **Complete / Frozen / Accepted**
([eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md);
[ADR-010](adr/010_opportunity_discovery_ingress.md)). M1 freezes discovery contracts
([eval/fr018_m1_discovery_contracts.md](eval/fr018_m1_discovery_contracts.md)).
M2 adds executable URL ingress
([eval/fr018_m2_url_discovery_ingress.md](eval/fr018_m2_url_discovery_ingress.md)).
M3 hardens SEEK + TLS and documents LinkedIn/Indeed limits
([eval/fr018_m3_production_hardening.md](eval/fr018_m3_production_hardening.md)).
M4 adds email job-alert acquisition with URL enrich
([eval/fr018_m4_email_job_alert_acquisition.md](eval/fr018_m4_email_job_alert_acquisition.md)).
M0: [eval/fr018_m0_engineering_spike.md](eval/fr018_m0_engineering_spike.md).

| Area | Coverage |
|------|----------|
| Contracts | `OpportunitySource` (`url` \| `email`), `DiscoveryRequest` / `DiscoveryOutcome`, Protocol |
| Provenance | `assert_url_acquisition_provenance`, `assert_email_acquisition_provenance` |
| URL adapter / thin ingress | Fake HTTP fixtures; SEEK production; LinkedIn/Indeed attempt + fail-closed |
| Email adapter (M4) | `.eml` fixtures; SEEK/LinkedIn/Indeed; digest expansion; **URL enrich** + fail-soft; definite skip |
| TLS (M3) | `build_default_ssl_context` / `truststore.SSLContext` |
| CLI | `cic opportunity discover`, `cic opportunity discover-email` |
| Unit | `tests/unit/discovery/` |
| Live acceptance | LinkedIn `.eml` → enrich → full Horizon 1A; re-run skipped=6 |
| Network / IMAP / Playwright | IMAP/Playwright **out of scope**; CI offline; live SEEK URL validated; email = owner-supplied files |
| Acceptance | [eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md) |
