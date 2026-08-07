<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/06_domain_model.md
Mode: section snapshot ('### Opportunity Discovery & Acquisition (FR-018)' → '### Job Posting')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

### Opportunity Discovery & Acquisition (FR-018)

**Maps to:** FR-018 (**Complete / Frozen / Accepted** —
[eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md))

Lawful channel adapters under a thin ingress into frozen Horizon 1A:

- **URL channel** — owner-supplied SEEK (production) / LinkedIn / Indeed (attempt).
- **Email channel** — owner-saved job-alert `.eml`; job URL is the durable identity
  facet; alert body is **discovery**. When the alert is card-only, enrich via
  existing URL acquisition (fail-soft). Provenance stays `source_kind=email`.

Email is not an authoritative job description. Playwright / IMAP / Easy Apply are
out of FR-018 freeze scope.

---
