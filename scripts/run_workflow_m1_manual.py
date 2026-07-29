#!/usr/bin/env python3
"""Deprecated entry point — use ``scripts/run_fr008_workflow_manual.py``."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_fr008_workflow_manual import main  # noqa: E402

warnings.warn(
    "scripts/run_workflow_m1_manual.py is deprecated; "
    "use scripts/run_fr008_workflow_manual.py",
    DeprecationWarning,
    stacklevel=1,
)

if __name__ == "__main__":
    raise SystemExit(main())
