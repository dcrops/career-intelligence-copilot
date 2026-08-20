# External/upload PDF filenames (AAS-0.1)

## Convention

Authoritative CIC artefacts stay:

    career-documents/**/generated/opp_<id>.pdf

Employer-facing copies live under the application package:

    data/application_packages/<opportunity_id>/export/
        <Candidate> - <Employer> - <Role> - CV.pdf
        <Candidate> - <Employer> - <Role> - Cover Letter.pdf

Byte-identical to the truth-approved authoritative PDFs. Opportunity IDs never
appear in export filenames. Spaces and ` - ` separators are intentional.

Windows classic MAX_PATH (~259) applies to the **absolute** destination, not
just the filename component. A 180-character filename cap is not enough when
`data/application_packages/<id>/export/` is already long (CSK Nexus prepare
measured prefix 130; Cover Letter `.pdf.tmp` reached 266). Naming now fits
`export_dir / filename` and the atomic `.pdf.tmp` path to a conservative 240
characters. Canonical company/title stay on the manifest; employer-facing
names may use the leading role before `|` and further deterministic shortening
only when the path budget requires it. Existing short names are unchanged.

## Code

- `career_intelligence.application_package.external_upload`
- `ApplicationPackageService.ensure_external_upload_pdfs` (also after `prepare`)
- AAS-0 `load_inputs` uploads export paths
- AAS-0.1 `upload_artefacts.assert_safe_external_upload_pdf` fail-closes at
  preflight **and** immediately before résumé filechooser `set_files` / cover-letter
  `set_input_files`. Internal
  `opp_<ULID>.pdf` is refused; the path must be under `export/` and match the
  human-readable shape. No silent substitution.

Underscore naming in `spikes/aas0/session_handoff.py::propose_external_export_filename`
is obsolete for employer-facing uploads; production uses spaced names above.
