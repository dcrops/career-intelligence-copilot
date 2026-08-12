# AAS spike notes — employer-facing export filenames

## Problem

AAS-0 uploaded PDFs named `opp_<opportunity_id>.pdf`. That leaks internal IDs to
SEEK employers and pollutes SEEK CV storage with opaque names.

Desired examples:

- `David_Cropper_Repurpose_It_AI_Engineer_CV.pdf`
- `David_Cropper_Repurpose_It_AI_Engineer_Cover_Letter.pdf`

Internal `opportunity_id` remains metadata / SoT key — not the employer-facing filename.

## Smallest ownership point (proposal — not implemented in production)

**Own at packaging/export**, not in Playwright and not by renaming Career Profile
Markdown sources.

Recommended seam:

1. Keep durable drafts under `career-documents/**/generated/` with stable internal
   stems (`opportunity_id`) for regeneration/truth hashing.
2. At **Application Package prepare** (or a thin export helper called by package
   prepare / assist upload), produce or copy employer-facing PDFs with
   `propose_external_export_filename(...)` into a dedicated export dir
   (e.g. `career-documents/**/export/` or package artefact refs).
3. Browser assist / owner upload uses **export** paths only.

Spike helper (design + unit-tested):  
`spikes/aas0/session_handoff.py::propose_external_export_filename`

## Non-goals

- Do not redesign document architecture.
- Do not change truth validation content-hash roots without an FR.
- Do not rename Markdown sources to company/title slugs.

## Next engineering step (when authorized)

Smallest production change: optional export filename on package prepare + spike
upload preference for export path. Track as part of AAS-1 prep or a tiny FR-010
follow-on — owner decision.
