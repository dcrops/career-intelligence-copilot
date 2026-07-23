# ADR-002: Opportunity Persistence Foundation (M1)

**Status:** Accepted  
**Date:** 2026-07-23

## Context

Phase 2 exit requires durable opportunity tracking, outcome logging (FR-013 subset), and
ranked comparison of open opportunities. FR-001–FR-006 are complete, but assessments were
ephemeral (manual JSON dumps only). The owner approved Option C storage: structured
repository storage as the system of record, with CSV as an operational export only (M3).

## Decision

- Add package `career_intelligence.opportunities` with public `OpportunityService`.
- Use permanent ids `opp_<ULID>` (minimal Crockford ULID generator; no new dependency).
- Store lightweight records in `data/opportunities/index.yaml`.
- Persist immutable FR-002–FR-005 JSON snapshots under `data/opportunities/artifacts/{id}/`
  by default at create time.
- Put YAML access behind `OpportunityStore`; do not export the adapter from the public API.
- Default create status is `assessed`. Owner decisions, outcomes, CSV, and ranking are
  deferred to M2–M4.

## Consequences

Downstream milestones can key decisions, outcomes, and rankings on `opportunity_id`.
Re-assessment creates a new opportunity (artifacts are immutable). Duplicate detection
(FR-014) is not implemented; identity facets are stored for future use only.

## Guardrail

Code outside the opportunities package must not import `yaml_store` or depend on YAML
paths. Use `OpportunityService` / `career_intelligence.opportunities` only.
