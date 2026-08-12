"""Load Yahoo IMAP mailbox configuration (FR-019 M1).

Preferred path: ``config/local_secrets.env`` (gitignored).
Environment variables with the same names override file values (env wins).
Never log or echo the app password.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import MailboxConfigError

_DEFAULT_HOST = "imap.mail.yahoo.com"
_DEFAULT_PORT = 993
_DEFAULT_FOLDER = "CIC Job Alerts"
_DEFAULT_SECRETS_PATH = Path("config") / "local_secrets.env"

_SECRET_KEYS = frozenset(
    {
        "CIC_MAILBOX_APP_PASSWORD",
        "CIC_MAILBOX_PASSWORD",
    }
)


@dataclass(frozen=True)
class MailboxConfig:
    """Owner mailbox connection settings (no secrets in repr)."""

    host: str
    port: int
    user: str
    app_password: str
    folder: str
    mark_seen: bool = False

    def __repr__(self) -> str:
        return (
            f"MailboxConfig(host={self.host!r}, port={self.port}, "
            f"user={self.user!r}, folder={self.folder!r}, "
            f"mark_seen={self.mark_seen}, app_password='***')"
        )


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _truthy(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _redact_message(message: str, secrets: list[str]) -> str:
    redacted = message
    for secret in secrets:
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "***")
    return redacted


def load_mailbox_config(
    *,
    secrets_path: Path | None = None,
    environ: dict[str, str] | None = None,
) -> MailboxConfig:
    """Load mailbox config from optional secrets file + environment (env wins)."""
    env = environ if environ is not None else dict(os.environ)
    path = secrets_path if secrets_path is not None else _DEFAULT_SECRETS_PATH
    file_values: dict[str, str] = {}
    if path.is_file():
        file_values = _parse_env_file(path)

    def _get(key: str, default: str | None = None) -> str | None:
        if key in env and env[key] != "":
            return env[key]
        if key in file_values and file_values[key] != "":
            return file_values[key]
        return default

    host = _get("CIC_MAILBOX_HOST", _DEFAULT_HOST) or _DEFAULT_HOST
    port_raw = _get("CIC_MAILBOX_PORT", str(_DEFAULT_PORT)) or str(_DEFAULT_PORT)
    user = _get("CIC_MAILBOX_USER")
    password = _get("CIC_MAILBOX_APP_PASSWORD") or _get("CIC_MAILBOX_PASSWORD")
    folder = _get("CIC_MAILBOX_FOLDER", _DEFAULT_FOLDER) or _DEFAULT_FOLDER
    mark_seen = _truthy(_get("CIC_MAILBOX_MARK_SEEN"), default=False)

    missing: list[str] = []
    if not user:
        missing.append("CIC_MAILBOX_USER")
    if not password:
        missing.append("CIC_MAILBOX_APP_PASSWORD")
    if missing:
        raise MailboxConfigError(
            "Missing required mailbox configuration: " + ", ".join(missing),
            detail=(
                f"Create {_DEFAULT_SECRETS_PATH.as_posix()} from "
                "config/local_secrets.env.example, or set the variables in the environment."
            ),
        )

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise MailboxConfigError(
            "CIC_MAILBOX_PORT must be an integer",
            detail=_redact_message(str(exc), [password or ""]),
        ) from exc

    if port <= 0 or port > 65535:
        raise MailboxConfigError("CIC_MAILBOX_PORT out of range")

    return MailboxConfig(
        host=host,
        port=port,
        user=user or "",
        app_password=password or "",
        folder=folder,
        mark_seen=mark_seen,
    )


def redact_secrets(text: str, config: MailboxConfig | None = None) -> str:
    """Strip known secret values from diagnostic text."""
    secrets = []
    if config is not None:
        secrets.append(config.app_password)
    for key in _SECRET_KEYS:
        value = os.environ.get(key)
        if value:
            secrets.append(value)
    return _redact_message(text, secrets)
