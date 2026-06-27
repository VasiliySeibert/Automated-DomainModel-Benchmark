"""Smoke test for the bundled datasets.

Verifies:
- both JSON files exist and are well-formed
- schema is [{id, nlt, puml}, ...]
- kaiser has 45 entries, reference has 8
- the local parser parses 100% of both datasets
"""
from __future__ import annotations

from Data.Parser import PlantUMLParser
from Data import load_dataset, load_kaiser, load_reference


def test_load_kaiser_returns_45_models():
    rows = load_kaiser()
    assert isinstance(rows, list)
    assert len(rows) == 45
    for r in rows:
        assert {"id", "nlt", "puml"} <= set(r.keys())


def test_load_reference_returns_8_models():
    rows = load_reference()
    assert isinstance(rows, list)
    assert len(rows) == 8
    for r in rows:
        assert {"id", "nlt", "puml"} <= set(r.keys())


def test_dataset_unified_loader():
    assert load_dataset("kaiser") == load_kaiser()
    assert load_dataset("reference") == load_reference()


def test_parser_parses_all_kaiser_models():
    parser = PlantUMLParser(strict=False)
    failed: list[str] = []
    for r in load_kaiser():
        try:
            parser.parse(r["puml"])
        except Exception as e:
            failed.append(f"{r['id']}: {e}")
    assert not failed, f"kaiser parse failures: {failed[:3]}"


def test_parser_parses_all_reference_models():
    parser = PlantUMLParser(strict=False)
    failed: list[str] = []
    for r in load_reference():
        try:
            parser.parse(r["puml"])
        except Exception as e:
            failed.append(f"{r['id']}: {e}")
    assert not failed, f"reference parse failures: {failed[:3]}"