# Opportunities store (M1)

Structured repository storage for durable **Opportunity** records.

**System of record:** this directory (via `OpportunityService` / `OpportunityStore`).

**Layout:**

```
index.yaml                 # lightweight Opportunity registry
artifacts/<opp_<ULID>>/
  posting.json
  job_analysis.json
  assessment.json
  portfolio_match.json
  strategy.json
```

CSV export/import is **M3** (export ongoing; import = one-time migration only). Do not
treat `applications/application_tracker.csv` as authoritative for assessed opportunities.

Live index and artifact files are gitignored. Keep this README tracked.
