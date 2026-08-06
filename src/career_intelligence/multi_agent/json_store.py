"""JSON directory persistence for FR-016 orchestration runs."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .errors import OrchestrationRunNotFoundError, OrchestrationStorageError
from .models import Handoff, OperationalBrief, OrchestrationRun

DEFAULT_ORCHESTRATION_RUNS_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "orchestration_runs"
)


class JsonDirectoryOrchestrationStore:
    """Persist runs, handoffs, and briefs under ``data/orchestration_runs/``."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else DEFAULT_ORCHESTRATION_RUNS_ROOT
        self.handoffs_dir = self.root / "handoffs"
        self.briefs_dir = self.root / "briefs"

    def save(self, run: OrchestrationRun) -> OrchestrationRun:
        path = self.root / f"{run.orchestration_run_id}.json"
        self._atomic_write(path, run.model_dump(mode="json"))
        return run

    def load(self, orchestration_run_id: str) -> OrchestrationRun:
        path = self.root / f"{orchestration_run_id}.json"
        if not path.is_file():
            raise OrchestrationRunNotFoundError(
                f"Orchestration run not found: {orchestration_run_id}"
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return OrchestrationRun.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            raise OrchestrationStorageError(
                f"Could not load orchestration run {orchestration_run_id}: {error}"
            ) from error

    def exists(self, orchestration_run_id: str) -> bool:
        return (self.root / f"{orchestration_run_id}.json").is_file()

    def save_handoff(self, handoff: Handoff) -> Handoff:
        path = self.handoffs_dir / f"{handoff.handoff_id}.json"
        self._atomic_write(path, handoff.model_dump(mode="json"))
        return handoff

    def load_handoff(self, handoff_id: str) -> Handoff:
        path = self.handoffs_dir / f"{handoff_id}.json"
        if not path.is_file():
            raise OrchestrationStorageError(f"Handoff not found: {handoff_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return Handoff.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            raise OrchestrationStorageError(
                f"Could not load handoff {handoff_id}: {error}"
            ) from error

    def save_brief(self, brief: OperationalBrief) -> OperationalBrief:
        path = self.briefs_dir / f"{brief.brief_id}.json"
        self._atomic_write(path, brief.model_dump(mode="json"))
        return brief

    def load_brief(self, brief_id: str) -> OperationalBrief:
        path = self.briefs_dir / f"{brief_id}.json"
        if not path.is_file():
            raise OrchestrationStorageError(f"Brief not found: {brief_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return OperationalBrief.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            raise OrchestrationStorageError(
                f"Could not load brief {brief_id}: {error}"
            ) from error

    def list_runs(self) -> list[OrchestrationRun]:
        if not self.root.is_dir():
            return []
        runs: list[OrchestrationRun] = []
        for path in sorted(self.root.glob("orr_*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                runs.append(OrchestrationRun.model_validate(raw))
            except (OSError, ValueError, ValidationError):
                continue
        runs.sort(key=lambda r: r.updated_at, reverse=True)
        return runs

    def _atomic_write(self, path: Path, payload: object) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
            temporary.write_text(text, encoding="utf-8", newline="\n")
            temporary.replace(path)
        except OSError as error:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
            raise OrchestrationStorageError(f"Could not write {path.name}: {error}") from error
