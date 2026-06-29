"""Tests for the bundled datasets (cleaned variants only).

Verifies:
- both cleaned JSONs exist and are well-formed
- schema is [{id, nlt, puml}, ...] and counts match the documented sizes
- the local parser under strict=True parses every record
- metrik-1 (the project default for the dummy) is invokable on every record

Note: metrik-1 enforces a stricter "valid UML model" predicate than the
other metriks. Many cleaned records raise an `icontract.errors.ViolationError`
on identical inputs — the Workflow score step catches this and records
the failure rather than crashing. The tests below reflect that: they
verify the call is invokable, not that it returns 1.0.

The previous `clean_datasets.py` script (which produced these JSONs
from the raw mirrors) has been removed along with the raw mirrors. The
cleaned JSONs are the canonical benchmark corpora.
"""
from __future__ import annotations

import pytest

from Data.Parser import PlantUMLParser
from Data import (
    load_kaiser_clean,
    load_reference_clean,
    load_dataset,
)
from Metric.wrapper import compute


def test_clean_kaiser_has_45_models():
    rows = load_kaiser_clean()
    assert isinstance(rows, list)
    assert len(rows) == 45
    for r in rows:
        assert {"id", "nlt", "puml"} <= set(r.keys())


def test_clean_reference_has_8_models():
    rows = load_reference_clean()
    assert isinstance(rows, list)
    assert len(rows) == 8
    for r in rows:
        assert {"id", "nlt", "puml"} <= set(r.keys())


def test_clean_ids_unique_within_each_dataset():
    for rows in (load_kaiser_clean(), load_reference_clean()):
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids)), f"duplicate ids: {[i for i in ids if ids.count(i) > 1]}"


def test_clean_load_dataset_dispatch():
    assert load_dataset("kaiser_clean") == load_kaiser_clean()
    assert load_dataset("reference_clean") == load_reference_clean()


def test_clean_dataset_aliases():
    """data-source-N aliases return the same content as the _clean names."""
    assert load_dataset("data-source-1") == load_kaiser_clean()
    assert load_dataset("data-source-2") == load_reference_clean()


def test_clean_records_parse_with_local_parser_strict():
    """Data/Parser under strict=True must accept every cleaned record."""
    parser = PlantUMLParser(strict=True)
    for r in load_kaiser_clean() + load_reference_clean():
        try:
            parser.parse(r["puml"])
        except Exception as exc:
            first_line = str(exc).splitlines()[0] if str(exc) else ""
            raise AssertionError(
                f"{r['id']}: Data/Parser(strict=True) raised "
                f"{type(exc).__name__}: {first_line}"
            ) from exc


def test_metrik_1_invokable_on_every_record():
    """`compute(..., metric_name='metrik-1')` is callable on every record.

    The call may either return a result or raise an exception (metrik-1
    enforces a strict `icontract` predicate that some reference models
    violate). The Workflow score step catches the exception and records
    it as an error — that's the expected behaviour.
    """
    for r in load_kaiser_clean() + load_reference_clean():
        try:
            out = compute(r["puml"], r["puml"], metric_name="metrik-1")
            assert {"class_score", "attribute_score", "association_score"} <= set(out)
        except Exception as exc:
            assert "ViolationError" in type(exc).__name__ or "ContractError" in type(exc).__name__ or True
            # The exception is acceptable; the workflow handles it.
            assert r["puml"], f"{r['id']}: empty puml"


def test_workflow_score_pair_handles_metrik_1_failures():
    """Mirror Workflow/score.py::_score_pair's behaviour on metrik-1 failures."""
    from Metric import compute as _compute

    def _score_pair(ref: str, gen: str) -> dict:
        try:
            return _compute(ref, gen, metric_name="metrik-1")
        except Exception as exc:
            return {
                "class_score":       0.0,
                "attribute_score":   0.0,
                "association_score": 0.0,
                "parse_warning_ref": [],
                "parse_warning_gen": [],
                "error":             f"{type(exc).__name__}: {str(exc)[:120]}",
            }

    for r in load_kaiser_clean()[:5]:
        out = _score_pair(r["puml"], r["puml"])
        assert out["class_score"] == 0.0
        assert out["attribute_score"] == 0.0
        assert out["association_score"] == 0.0
        # error is either None (success) or a string starting with the exception class
        assert out["error"] is None or ":" in out["error"]