# Application packages store (FR-010)

Structured repository storage for **Application Package** manifests.

**Layout:**

```
<data/application_packages>/
  <opp_<ULID>>/
    manifest.json
```

The manifest is the durable package record. It stores deterministic references to:

- immutable Opportunity evidence (`artifact_paths` for posting / job analysis /
  assessment / portfolio match / strategy)
- acquisition provenance copied from Opportunity identity
- generated CV and cover-letter draft **filenames** produced by existing FR-006 /
  FR-007 writers (relative to the service-configured output directories; resolved
  to absolute paths on `get`)

Generated document content is **not** duplicated here. One Opportunity has one
current package; regeneration replaces `manifest.json`. The prior manifest remains
current until a full `prepare` succeeds through manifest save.

Live package files are gitignored. Keep this README tracked.
