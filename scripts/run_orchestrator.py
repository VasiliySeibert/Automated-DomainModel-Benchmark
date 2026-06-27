#!/usr/bin/env python3
"""Top-level CLI shim for Workflow/orchestrator.py.

See Workflow/README.md for the import-order rationale.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import domain_model_metrics  # noqa: F401


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


orchestrator = _load(
    "_workflow_orchestrator", REPO_ROOT / "Workflow" / "orchestrator.py"
)

if __name__ == "__main__":
    sys.exit(orchestrator.main())