# Masterclass packaging — implementation note

**Date:** 2026-08-06  
**Scope:** FR-016 first package; pattern for future frozen FRs  
**Related:** [masterclass/README.md](README.md), [FR016/MANIFEST.md](FR016/MANIFEST.md),
`scripts/build_masterclass_package.py`

## How authoritative documentation is preserved

Engineering continues to live only under repository SoT paths (`docs/eval/`,
`docs/adr/`, functional specification, domain model, implementation notes, testing
strategy). The Masterclass package never becomes the edit surface.

## How duplication is avoided

`sources/` files are **generated snapshots** (full-file copy or mechanical heading
extract) with an explicit “DO NOT EDIT” banner and a regenerate command. They are
convenience mirrors for single-folder Academy attachment, not parallel documents.
After SoT changes: re-run the builder; do not patch snapshots by hand.

## How future FRs should adopt the same model

1. Freeze the FR (acceptance + ADR + navigation).
2. Create `docs/masterclass/FRnnn/{README.md,MANIFEST.md}`.
3. Register source mappings in `scripts/build_masterclass_package.py`.
4. Run `python scripts/build_masterclass_package.py FRnnn`.
5. Commit the package; attach `FRnnn/` for Academy generation.

Do not populate FR001–FR015 until the owner requests packaging for those FRs.
