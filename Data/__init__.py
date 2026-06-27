"""Benchmark datasets for automated domain modelling.

Public surface:
    load_kaiser()    -> list[dict]   (45 entries, id/nlt/puml)
    load_reference() -> list[dict]   (8 entries, id/nlt/puml)
    load(name)       -> list[dict]   unified loader for "kaiser" / "reference"
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

KAISER_PATH = DATA_DIR / "kaiser.json"
REFERENCE_PATH = DATA_DIR / "reference.json"


def load(path: Path) -> list[dict]:
    """Read a benchmark JSON file from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_kaiser() -> list[dict]:
    """45 synthetic domain models with NL text and PlantUML reference."""
    return load(KAISER_PATH)


def load_reference() -> list[dict]:
    """8 reference models with curated NL text and PlantUML."""
    return load(REFERENCE_PATH)


def load_dataset(name: str) -> list[dict]:
    """Unified loader: name in {'kaiser', 'reference'}."""
    if name == "kaiser":
        return load_kaiser()
    if name == "reference":
        return load_reference()
    raise ValueError(f"Unknown dataset {name!r}; expected 'kaiser' or 'reference'")


__all__ = [
    "DATA_DIR",
    "KAISER_PATH",
    "REFERENCE_PATH",
    "load",
    "load_kaiser",
    "load_reference",
    "load_dataset",
]