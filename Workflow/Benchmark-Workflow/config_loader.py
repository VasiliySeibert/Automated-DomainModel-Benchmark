"""Workflow/Benchmark-Workflow configuration loader.

Reads `Workflow/Benchmark-Workflow/config.json` (paired with this
file) and exposes typed accessors for the model registry, dataset
list, and metric name.

This loader is legacy — the active pipeline (`generate.py`,
`score.py`, `visualise.py`) no longer consults `config.json`.
It is preserved for future model iteration.

Score bucket boundaries live in `Metric/wrapper.py` as
`BUCKETS` / `BUCKET_LABELS` (single source of truth).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
CONFIG_PATH = THIS_DIR / "config.json"


def load() -> dict[str, Any]:
    """Return the full config dict."""
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def models() -> list[dict[str, str]]:
    """Return the model registry list."""
    return load()["models"]


def model_by_short(short: str) -> dict[str, str] | None:
    """Return one model entry by its short name, or None."""
    for m in models():
        if m["short"] == short:
            return m
    return None


def model_ids() -> list[str]:
    """Return all model_ids in order."""
    return [m["model_id"] for m in models()]


def model_shorts() -> list[str]:
    """Return all model short names in order."""
    return [m["short"] for m in models()]


def datasets() -> list[str]:
    return list(load()["datasets"])


def metric_name() -> str:
    return load().get("metric", "metrik-4")


__all__ = [
    "CONFIG_PATH", "load",
    "models", "model_by_short", "model_ids", "model_shorts",
    "datasets", "metric_name",
]
