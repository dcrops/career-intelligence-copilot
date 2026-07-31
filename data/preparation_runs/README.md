# Preparation orchestration runs (FR-011)

Structured recovery/audit storage for **Application Preparation** runs.

**Layout:**

```
<data/preparation_runs>/
  apr_<ULID>.json
```

These files are **not** the Opportunity system of record and **not** package
manifests. They record orchestration progress only (`validate_preconditions` →
`prepare_package`). Package artefacts remain under `data/application_packages/`.
