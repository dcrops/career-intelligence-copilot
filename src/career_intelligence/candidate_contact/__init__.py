"""Owner-authoritative candidate contact for external application documents.

Separate from CareerProfile (decision-support evidence). Values load from
``config/candidate_contact.yaml`` and map to FR-006 ``ContactDetails``.
"""

from __future__ import annotations

from .config import (
    DEFAULT_CONTACT_PATH,
    REQUIRED_CONTACT_FIELDS,
    load_candidate_contact,
    require_contact_details,
)
from .errors import CandidateContactConfigError

__all__ = [
    "CandidateContactConfigError",
    "DEFAULT_CONTACT_PATH",
    "REQUIRED_CONTACT_FIELDS",
    "load_candidate_contact",
    "require_contact_details",
]
