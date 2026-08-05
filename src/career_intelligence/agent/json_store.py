"""JSON directory adapter for agent runs under ``data/agent_runs/``."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .errors import AgentRunNotFoundError, AgentStorageError
from .models import AgentRun

DEFAULT_AGENT_RUNS_ROOT = Path(__file__).resolve().parents[3] / "data" / "agent_runs"


class JsonDirectoryAgentRunStore:
    """Persist one JSON file per run: ``{root}/{agent_run_id}.json``."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else DEFAULT_AGENT_RUNS_ROOT

    def save(self, run: AgentRun) -> AgentRun:
        path = self._path(run.agent_run_id)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            payload = (
                json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False)
                + "\n"
            )
            temporary.write_text(payload, encoding="utf-8", newline="\n")
            temporary.replace(path)
        except OSError as error:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
            raise AgentStorageError(
                f"Could not write agent run {run.agent_run_id}: {error}"
            ) from error
        return run

    def load(self, agent_run_id: str) -> AgentRun:
        path = self._path(agent_run_id)
        if not path.is_file():
            raise AgentRunNotFoundError(f"Agent run not found: {agent_run_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return AgentRun.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            raise AgentStorageError(
                f"Could not load agent run {agent_run_id}: {error}"
            ) from error

    def exists(self, agent_run_id: str) -> bool:
        return self._path(agent_run_id).is_file()

    def list_runs(self) -> list[AgentRun]:
        """Load all agent runs (newest updated_at first). Missing root → empty."""
        if not self.root.is_dir():
            return []
        runs: list[AgentRun] = []
        for path in sorted(self.root.glob("agr_*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                runs.append(AgentRun.model_validate(raw))
            except (OSError, ValueError, ValidationError):
                continue
        runs.sort(key=lambda r: r.updated_at, reverse=True)
        return runs

    def _path(self, agent_run_id: str) -> Path:
        return self.root / f"{agent_run_id}.json"
