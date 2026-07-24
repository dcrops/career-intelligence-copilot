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

**M2:** Owner decisions and outcomes update `index.yaml` only. Artifact snapshots under
`artifacts/` remain immutable.

**M3:** `cic opportunity export-csv` writes a derived spreadsheet under
`data/exports/` (or `--output`). `cic opportunity import-legacy-csv` is a one-time
migration utility with `--dry-run`; it does not sync continuously.

Live index and artifact files are gitignored. Keep this README tracked.
