"""Unit tests for FR-019 M1 mailbox configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.mailbox.config import (
    MailboxConfig,
    load_mailbox_config,
    redact_secrets,
)
from career_intelligence.mailbox.errors import MailboxConfigError


def test_load_from_secrets_file(tmp_path: Path) -> None:
    path = tmp_path / "local_secrets.env"
    path.write_text(
        "\n".join(
            [
                "CIC_MAILBOX_HOST=imap.mail.yahoo.com",
                "CIC_MAILBOX_PORT=993",
                "CIC_MAILBOX_USER=owner@yahoo.com",
                "CIC_MAILBOX_APP_PASSWORD=super-secret-app-password",
                "CIC_MAILBOX_FOLDER=CIC Job Alerts",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = load_mailbox_config(secrets_path=path, environ={})
    assert config.user == "owner@yahoo.com"
    assert config.app_password == "super-secret-app-password"
    assert config.folder == "CIC Job Alerts"
    assert config.mark_seen is False
    assert "super-secret" not in repr(config)


def test_environment_overrides_file(tmp_path: Path) -> None:
    path = tmp_path / "local_secrets.env"
    path.write_text(
        "CIC_MAILBOX_USER=file@yahoo.com\n"
        "CIC_MAILBOX_APP_PASSWORD=file-secret\n",
        encoding="utf-8",
    )
    config = load_mailbox_config(
        secrets_path=path,
        environ={
            "CIC_MAILBOX_USER": "env@yahoo.com",
            "CIC_MAILBOX_APP_PASSWORD": "env-secret",
            "CIC_MAILBOX_FOLDER": "Alerts",
        },
    )
    assert config.user == "env@yahoo.com"
    assert config.app_password == "env-secret"
    assert config.folder == "Alerts"


def test_missing_required_keys_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "empty.env"
    path.write_text("# empty\n", encoding="utf-8")
    with pytest.raises(MailboxConfigError, match="CIC_MAILBOX_USER"):
        load_mailbox_config(secrets_path=path, environ={})


def test_password_redacted_from_diagnostics() -> None:
    config = MailboxConfig(
        host="imap.mail.yahoo.com",
        port=993,
        user="owner@yahoo.com",
        app_password="hunter2-app-pass",
        folder="CIC Job Alerts",
    )
    text = redact_secrets("login failed hunter2-app-pass for user", config)
    assert "hunter2-app-pass" not in text
    assert "***" in text
