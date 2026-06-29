"""Smoke test for the bundled datasets.

Verifies:
- both JSON files exist and are well-formed
- schema is [{id, nlt, puml}, ...]
- kaiser_clean has 45 entries, reference_clean has 8
- the local parser parses 100% of both datasets
"""
from __future__ import annotations

from Data.Parser import PlantUMLParser
from Data import (
    KAISER_CLEAN_PATH,
    REFERENCE_CLEAN_PATH,
    load_dataset,
    load_kaiser_clean,
    load_reference_clean,
)


def test_kaiser_clean_file_exists():
    assert KAISER_CLEAN_PATH.is_file()


def test_reference_clean_file_exists():
    assert REFERENCE_CLEAN_PATH.is_file()


def test_load_kaiser_clean_returns_45_models():
    rows = load_kaiser_clean()
    assert isinstance(rows, list)
    assert len(rows) == 45
    for r in rows:
        assert {"id", "nlt", "puml"} <= set(r.keys())


def test_load_reference_clean_returns_8_models():
    rows = load_reference_clean()
    assert isinstance(rows, list)
    assert len(rows) == 8
    for r in rows:
        assert {"id", "nlt", "puml"} <= set(r.keys())


def test_dataset_unified_loader():
    assert load_dataset("kaiser_clean") == load_kaiser_clean()
    assert load_dataset("reference_clean") == load_reference_clean()
    assert load_dataset("data-source-1") == load_kaiser_clean()
    assert load_dataset("data-source-2") == load_reference_clean()


def test_dataset_unified_loader_rejects_unknown():
    import pytest
    with pytest.raises(ValueError):
        load_dataset("kaiser")


def test_parser_parses_all_kaiser_clean_models():
    parser = PlantUMLParser(strict=False)
    failed: list[str] = []
    for r in load_kaiser_clean():
        try:
            parser.parse(r["puml"])
        except Exception as e:
            failed.append(f"{r['id']}: {e}")
    assert not failed, f"kaiser_clean parse failures: {failed[:3]}"


def test_parser_parses_all_reference_clean_models():
    parser = PlantUMLParser(strict=False)
    failed: list[str] = []
    for r in load_reference_clean():
        try:
            parser.parse(r["puml"])
        except Exception as e:
            failed.append(f"{r['id']}: {e}")
    assert not failed, f"reference_clean parse failures: {failed[:3]}"