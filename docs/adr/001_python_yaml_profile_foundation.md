# ADR-001: Python and YAML Career Profile Foundation

**Status:** Accepted  
**Date:** 2026-07-19

## Context

FR-001 requires an updatable structured career profile that is available to every later
decision. The repository had no implementation stack or architecture before Phase 2 began.
The first slice must support the active single-user job search without introducing infrastructure
for hypothetical scale.

## Decision

- Use Python 3.11+ and Pydantic v2 for typed domain models.
- Store one career profile in a human-readable YAML file.
- Put YAML access behind a small `ProfileStore` protocol.
- Expose the profile to downstream capabilities only through `CareerProfileService` and the
  public `career_intelligence.profile` package.
- Provide a thin Typer CLI for `validate`, `summary`, `show`, and `init`.
- Represent skills with an objective name and optional evidence reference. Do not store
  self-assessed proficiency.
- Represent project evidence through `demonstrates`.
- Populate the first profile manually from the Master CV.

## Consequences

The owner can inspect and edit the profile directly, while downstream requirements receive a
stable typed representation. YAML can later be replaced without materially changing consumers.
Manual editing and single-file persistence are deliberate constraints for this slice.

The service retains full-model `save` for validated persistence and initialization. Partial
update APIs, profile history, databases, user interfaces, PDF parsing, and multi-user support
are deferred.

## Guardrail

Code outside the career-profile implementation must not import the YAML adapter or depend on
file paths, PyYAML, or YAML-specific structures. Storage replacement should require changes
inside the profile capability, not in downstream decision stages.
