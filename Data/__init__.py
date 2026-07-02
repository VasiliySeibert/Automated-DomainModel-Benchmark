"""Benchmark datasets for automated domain modelling.

Three data sources live under `Data/`, each in its own subfolder:

    Data/data-source-1/kaiser_clean.json              (45 entries)
    Data/data-source-2/reference_clean.json           (8 entries)
    Data/data-source-3/data_source_3_clean.json       (45 entries; TU-Wien)

All three files are parser-cleaned variants — they parse under the strict
mode used by the metrik-N scorers without raising.

Public surface:
    load_kaiser_clean()          -> list[dict]
    load_reference_clean()       -> list[dict]
    load_data_source_3_clean()   -> list[dict]
    load_dataset(name)           -> list[dict]   unified loader

Accepted names for `load_dataset`:
    'kaiser_clean' / 'data-source-1'  -> 45 cleaned models
    'reference_clean' / 'data-source-2' -> 8 cleaned models
    'data_source_3_clean' / 'data-source-3' -> 45 cleaned models
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

KAISER_CLEAN_PATH = DATA_DIR / "data-source-1" / "kaiser_clean.json"
REFERENCE_CLEAN_PATH = DATA_DIR / "data-source-2" / "reference_clean.json"
DATA_SOURCE_3_CLEAN_PATH = DATA_DIR / "data-source-3" / "data_source_3_clean.json"


def load(path: Path) -> list[dict]:
    """Read a benchmark JSON file from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_kaiser_clean() -> list[dict]:
    """45 cleaned models from data-source-1."""
    return load(KAISER_CLEAN_PATH)


def load_reference_clean() -> list[dict]:
    """8 cleaned models from data-source-2."""
    return load(REFERENCE_CLEAN_PATH)


def load_data_source_3_clean() -> list[dict]:
    """45 cleaned models from data-source-3 (TU-Wien)."""
    return load(DATA_SOURCE_3_CLEAN_PATH)


_LOADERS: dict[str, callable] = {
    "kaiser_clean":          load_kaiser_clean,
    "data-source-1":         load_kaiser_clean,
    "reference_clean":       load_reference_clean,
    "data-source-2":         load_reference_clean,
    "data_source_3_clean":   load_data_source_3_clean,
    "data-source-3":         load_data_source_3_clean,
}


def load_dataset(name: str) -> list[dict]:
    """Unified loader.

    Accepted names:
        'kaiser_clean' / 'data-source-1'  -> 45 cleaned models
        'reference_clean' / 'data-source-2' -> 8 cleaned models
        'data_source_3_clean' / 'data-source-3' -> 45 cleaned models
    """
    if name not in _LOADERS:
        raise ValueError(
            f"Unknown dataset {name!r}; "
            "expected one of: " + ", ".join(sorted(_LOADERS))
        )
    return _LOADERS[name]()


__all__ = [
    "DATA_DIR",
    "KAISER_CLEAN_PATH",
    "REFERENCE_CLEAN_PATH",
    "DATA_SOURCE_3_CLEAN_PATH",
    "load",
    "load_kaiser_clean",
    "load_reference_clean",
    "load_data_source_3_clean",
    "load_dataset",
]