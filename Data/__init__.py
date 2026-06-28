"""Benchmark datasets for automated domain modelling.

Public surface:
    load_kaiser()         -> list[dict]   (45 entries, raw mirrors of upstream)
    load_reference()      -> list[dict]   (8 entries, raw mirrors of upstream)
    load_kaiser_clean()   -> list[dict]   (45 entries, parser-cleaned)
    load_reference_clean()-> list[dict]   (8 entries, parser-cleaned)
    load_dataset(name)    -> list[dict]   unified loader

The `_clean` variants are produced by `Data/clean_datasets.py` and are the
recommended scoring references — the metric pipeline (`metrik-4`) uses
`strict=True` parsing, so the raw mirrors raise on 17/53 records.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

KAISER_PATH = DATA_DIR / "kaiser.json"
REFERENCE_PATH = DATA_DIR / "reference.json"
KAISER_CLEAN_PATH = DATA_DIR / "kaiser_clean.json"
REFERENCE_CLEAN_PATH = DATA_DIR / "reference_clean.json"


def load(path: Path) -> list[dict]:
    """Read a benchmark JSON file from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_kaiser() -> list[dict]:
    """45 synthetic domain models with NL text and PlantUML reference (raw)."""
    return load(KAISER_PATH)


def load_reference() -> list[dict]:
    """8 reference models with curated NL text and PlantUML (raw)."""
    return load(REFERENCE_PATH)


def load_kaiser_clean() -> list[dict]:
    """45 cleaned models — see Data/clean_datasets.py for the rewrites."""
    return load(KAISER_CLEAN_PATH)


def load_reference_clean() -> list[dict]:
    """8 cleaned models — see Data/clean_datasets.py for the rewrites."""
    return load(REFERENCE_CLEAN_PATH)


def load_dataset(name: str) -> list[dict]:
    """Unified loader.

    Accepted names:
        'kaiser'           — raw kaiser.json
        'reference'        — raw reference.json
        'kaiser_clean'     — parser-cleaned kaiser.json
        'reference_clean'  — parser-cleaned reference.json
    """
    if name == "kaiser":
        return load_kaiser()
    if name == "reference":
        return load_reference()
    if name == "kaiser_clean":
        return load_kaiser_clean()
    if name == "reference_clean":
        return load_reference_clean()
    raise ValueError(
        f"Unknown dataset {name!r}; "
        "expected 'kaiser', 'reference', 'kaiser_clean', or 'reference_clean'"
    )


__all__ = [
    "DATA_DIR",
    "KAISER_PATH",
    "REFERENCE_PATH",
    "KAISER_CLEAN_PATH",
    "REFERENCE_CLEAN_PATH",
    "load",
    "load_kaiser",
    "load_reference",
    "load_kaiser_clean",
    "load_reference_clean",
    "load_dataset",
]