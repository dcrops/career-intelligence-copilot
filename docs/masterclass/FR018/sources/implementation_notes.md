<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/08_implementation_notes.md
Mode: section snapshot ('## FR-018 Opportunity Discovery & Acquisition (complete / frozen)' → '### FR-008 acquisition foundation (complete — closes FR-008)')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Sibling PDF is rendered automatically by the same command (or: python scripts/render_masterclass_pdf.py --package <FR_ID>).
Repository documentation remains the source of truth.
-->

## FR-018 Opportunity Discovery & Acquisition (complete / frozen)

**Status:** Complete / Frozen / Accepted (2026-08-07). Acceptance:
[docs/eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md).
ADR: [docs/adr/010_opportunity_discovery_ingress.md](adr/010_opportunity_discovery_ingress.md).

| Symbol | Role |
|--------|------|
| `ThinDiscoveryIngress` | Thin coordinator → existing runner |
| `UrlAcquisitionAdapter` | Fetch + extract one supported job URL |
| `EmailAcquisitionAdapter` | `.eml#job=N`; optional URL enrich |
| `parse_job_alert_email` | SEEK / LinkedIn / Indeed allow-list |
| `cic opportunity discover` / `discover-email` | Owner CLI |
| Provenance asserts | Fail-closed URL + email |

Live: LinkedIn alert enrich → full Horizon 1A; definite skip on re-run. No IMAP /
Playwright / Easy Apply in FR-018.

### FR-018 M4 email job-alert acquisition (complete)

**Status:** Accepted (2026-08-07). Eval:
[docs/eval/fr018_m4_email_job_alert_acquisition.md](eval/fr018_m4_email_job_alert_acquisition.md).

| Symbol | Role |
|--------|------|
| `EmailAcquisitionAdapter` | One job from `.eml#job=N` → `source_kind=email` (+ URL enrich) |
| `parse_job_alert_email` | MIME parse; SEEK/LinkedIn/Indeed allow-list |
| `cic opportunity discover-email` | Owner CLI for saved alerts |
| `assert_email_acquisition_provenance` | Fail-closed email provenance |

M4 does **not** implement IMAP, recruiter CRM, or Playwright.

### FR-018 M3 production hardening (complete)

**Status:** Complete (2026-08-07). Eval:
[docs/eval/fr018_m3_production_hardening.md](eval/fr018_m3_production_hardening.md).

| Symbol | Role |
|--------|------|
| `build_default_ssl_context` / `UrllibHttpClient` | OS trust-store TLS for live fetch |
| SEEK canonical | Stable `www.seek.com.au/job/<id>` across host variants |
| LinkedIn gates | Fail closed on expired/listing redirects |
| `cic opportunity discover` | Owner CLI (SEEK production path) |

M3 does **not** implement email, feeds, Playwright, or Cloudflare bypass.

### FR-018 M2 URL discovery ingress (complete)

**Status:** Complete (2026-08-07). Eval:
[docs/eval/fr018_m2_url_discovery_ingress.md](eval/fr018_m2_url_discovery_ingress.md).

| Symbol | Role |
|--------|------|
| `UrlAcquisitionAdapter` | Fetch + extract one supported job URL |
| `ThinDiscoveryIngress` | Thin coordinator → existing runner |
| `FakeHttpClient` / `UrllibHttpClient` | Offline vs live fetch |
| `cic opportunity discover` | Owner CLI |

M2 does **not** implement email, feeds, Playwright, or scheduled discovery.
