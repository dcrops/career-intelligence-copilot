"""Load owner-authoritative candidate contact for application composition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from career_intelligence.cv_generation.options import ContactDetails

from .errors import CandidateContactConfigError

DEFAULT_CONTACT_PATH = Path("config") / "candidate_contact.yaml"

REQUIRED_CONTACT_FIELDS: tuple[str, ...] = (
    "email",
    "phone",
    "location",
    "linkedin_url",
    "portfolio_url",
    "github_url",
)

_URL_FIELDS = frozenset({"linkedin_url", "portfolio_url", "github_url"})


def load_candidate_contact(
    path: Path | None = None,
    *,
    require_complete: bool = True,
) -> ContactDetails:
    """Load ContactDetails from owner YAML config.

    Raises CandidateContactConfigError when the file is missing/unreadable or
    required fields are absent/blank (when require_complete is True).
    """
    config_path = path if path is not None else DEFAULT_CONTACT_PATH
    if not config_path.is_file():
        raise CandidateContactConfigError(
            "Application preparation blocked:\n"
            "candidate contact configuration incomplete.\n\n"
            "Missing:\n"
            "- (contact config file)\n\n"
            f"Update:\n{config_path.as_posix()}\n\n"
            "Copy config/candidate_contact.yaml.example and fill owner values."
        )
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CandidateContactConfigError(
            f"Application preparation blocked:\n"
            f"could not read candidate contact configuration at "
            f"{config_path.as_posix()}: {error}"
        ) from error
    except yaml.YAMLError as error:
        raise CandidateContactConfigError(
            f"Application preparation blocked:\n"
            f"candidate contact configuration is not valid YAML "
            f"({config_path.as_posix()}): {error}"
        ) from error

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise CandidateContactConfigError(
            "Application preparation blocked:\n"
            "candidate contact configuration must be a YAML mapping.\n\n"
            f"Update:\n{config_path.as_posix()}"
        )

    payload = {str(key): value for key, value in raw.items() if value is not None}
    missing = [
        field
        for field in REQUIRED_CONTACT_FIELDS
        if not _non_empty_str(payload.get(field))
    ]
    if require_complete and missing:
        missing_lines = "\n".join(f"- {name}" for name in missing)
        raise CandidateContactConfigError(
            "Application preparation blocked:\n"
            "candidate contact configuration incomplete.\n\n"
            f"Missing:\n{missing_lines}\n\n"
            f"Update:\n{config_path.as_posix()}"
        )

    try:
        contact = ContactDetails.model_validate(
            {key: payload[key] for key in REQUIRED_CONTACT_FIELDS if key in payload}
            | {
                key: payload[key]
                for key in payload
                if key not in REQUIRED_CONTACT_FIELDS
            }
        )
    except Exception as error:  # noqa: BLE001 — surface as owner-facing config error
        raise CandidateContactConfigError(
            "Application preparation blocked:\n"
            "candidate contact configuration failed validation.\n\n"
            f"{error}\n\n"
            f"Update:\n{config_path.as_posix()}"
        ) from error

    if require_complete:
        _assert_url_shapes(contact, config_path)
    return contact


def require_contact_details(
    contact: ContactDetails | None,
    *,
    config_path: Path | None = None,
) -> ContactDetails:
    """Fail closed when ContactDetails is missing required external-package fields."""
    path = config_path if config_path is not None else DEFAULT_CONTACT_PATH
    if contact is None:
        raise CandidateContactConfigError(
            "Application preparation blocked:\n"
            "candidate contact configuration incomplete.\n\n"
            "Missing:\n"
            "- (all required contact fields)\n\n"
            f"Update:\n{path.as_posix()}"
        )
    payload = contact.model_dump(exclude_none=True)
    missing = [
        field
        for field in REQUIRED_CONTACT_FIELDS
        if not _non_empty_str(payload.get(field))
    ]
    if missing:
        missing_lines = "\n".join(f"- {name}" for name in missing)
        raise CandidateContactConfigError(
            "Application preparation blocked:\n"
            "candidate contact configuration incomplete.\n\n"
            f"Missing:\n{missing_lines}\n\n"
            f"Update:\n{path.as_posix()}"
        )
    _assert_url_shapes(contact, path)
    return contact


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _assert_url_shapes(contact: ContactDetails, config_path: Path) -> None:
    for field in _URL_FIELDS:
        value = getattr(contact, field, None)
        if not value:
            continue
        if not str(value).startswith(("http://", "https://")):
            raise CandidateContactConfigError(
                "Application preparation blocked:\n"
                f"{field} must be an absolute http(s) URL.\n\n"
                f"Update:\n{config_path.as_posix()}"
            )
