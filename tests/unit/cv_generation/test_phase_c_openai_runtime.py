"""Regression: Phase C OpenAI runtime prep matches FR-002/003 manual path."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "scripts" / "run_cv_generation_manual.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_cv_generation_manual", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_prepare_openai_runtime_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _load_runner()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        runner._prepare_openai_runtime_for_summary_rewrite()


def test_prepare_openai_runtime_injects_truststore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    calls: list[str] = []

    class _FakeTruststore:
        @staticmethod
        def inject_into_ssl() -> None:
            calls.append("injected")

    monkeypatch.setitem(sys.modules, "truststore", _FakeTruststore)
    runner._prepare_openai_runtime_for_summary_rewrite()
    assert calls == ["injected"]
