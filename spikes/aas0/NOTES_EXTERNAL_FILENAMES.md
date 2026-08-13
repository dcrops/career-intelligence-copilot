# External/upload PDF filenames (AAS-0 dogfood follow-up)

## Convention

Authoritative CIC artefacts stay:

    career-documents/**/generated/opp_<id>.pdf

Employer-facing copies live under the application package:

    data/application_packages/<opportunity_id>/export/
        <Candidate> - <Employer> - <Role> - CV.pdf
        <Candidate> - <Employer> - <Role> - Cover Letter.pdf

Byte-identical to the truth-approved authoritative PDFs. Opportunity IDs never
appear in export filenames. Spaces and ` - ` separators are intentional.

## Code

- `career_intelligence.application_package.external_upload`
- `ApplicationPackageService.ensure_external_upload_pdfs` (also after `prepare`)
- AAS-0 `load_inputs` uploads export paths

Underscore naming in `spikes/aas0/session_handoff.py::propose_external_export_filename`
is obsolete for employer-facing uploads; production uses spaced names above.
