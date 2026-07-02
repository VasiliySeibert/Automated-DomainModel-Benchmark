"""Tests for the diagram extractor.

We verify that the parser handles all three datasets without errors and
that the per-record summary fields have the right types.
"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NLP_ROOT = HERE.parent
REPO = NLP_ROOT.parent.parent
for p in (str(REPO), str(NLP_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from extract_diagram import extract, summarise  # noqa: E402

DATASETS = [
    (NLP_ROOT.parent / "data-source-1" / "kaiser_clean.json", "kaiser"),
    (NLP_ROOT.parent / "data-source-2" / "reference_clean.json", "reference"),
    (NLP_ROOT.parent / "data-source-3" / "data_source_3_clean.json", "data_source_3"),
]


@pytest.mark.parametrize("path,label", DATASETS)
def test_parse_all_records(path, label):
    data = json.load(open(path))
    failures = []
    for rec in data:
        try:
            d = extract(rec["puml"])
            s = summarise(d)
            assert s["n_classes"] >= 0
            assert s["n_relationships"] >= 0
        except Exception as e:
            failures.append((rec["id"], repr(e)))
    assert not failures, f"{label} parser failures: {failures[:3]}"


def test_airtravel_summary_known_values():
    """The AirTravel diagram has 12 classes, 18 relationships."""
    data = json.load(open(NLP_ROOT.parent / "data-source-1" / "kaiser_clean.json"))
    rec = next(r for r in data if r["id"] == "AirTravel")
    d = extract(rec["puml"])
    s = summarise(d)
    assert s["n_classes"] == 12
    assert s["n_relationships"] == 18
