# Owner-local configuration that must not enter Git.

| File | In Git? | Purpose |
|------|---------|---------|
| `local_secrets.env.example` | Yes | Keys-only template for FR-019 Yahoo IMAP (and future scheduled runs) |
| `local_secrets.env` | **No** (gitignored) | Owner credentials — copy from the example and fill in |
| `candidate_contact.yaml.example` | Yes | Fictional template for application contact/navigation |
| `candidate_contact.yaml` | **No** (gitignored) | Owner email/phone/location/LinkedIn/portfolio/GitHub for external packages |

## Mailbox secrets

**Preferred path:** edit `config/local_secrets.env`.  
**Override:** set the same `CIC_MAILBOX_*` variables in the process environment
(environment wins). See [docs/eval/fr019_m1_mailbox_intake.md](../docs/eval/fr019_m1_mailbox_intake.md).

Never commit real Yahoo app passwords or log them.

## Candidate contact (application documents)

External package prepare / preparation / agent paths load
`config/candidate_contact.yaml` into FR-006 `ContactDetails`. This is
application-composition data — not CareerProfile evidence and not mailbox
secrets.

Copy `candidate_contact.yaml.example` → `candidate_contact.yaml` and fill real
values. Incomplete config fails closed before package generation.
