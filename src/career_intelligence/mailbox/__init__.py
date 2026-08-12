"""FR-019 M1 — Yahoo mailbox intake (automatic job-alert obtainment).

Composes FR-018 email discovery; does not replace parsers, ingress, or Opportunity SoT.
"""

from __future__ import annotations

from .config import MailboxConfig, MailboxConfigError, load_mailbox_config
from .drop_folder import list_eml_files
from .errors import MailboxError, MailboxImapError, MailboxIntakeError
from .intake import MailboxIntakeResult, MailboxIntakeService, run_mailbox_intake
from .ledger import EmailIntakeLedger
from .models import IngestedMailMessage, IntakeMessageOutcome

__all__ = [
    "EmailIntakeLedger",
    "IngestedMailMessage",
    "IntakeMessageOutcome",
    "MailboxConfig",
    "MailboxConfigError",
    "MailboxError",
    "MailboxImapError",
    "MailboxIntakeError",
    "MailboxIntakeResult",
    "MailboxIntakeService",
    "list_eml_files",
    "load_mailbox_config",
    "run_mailbox_intake",
]
