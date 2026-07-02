"""Tests for the cross-reference between kaiser_clean and data_source_3."""
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

from extract_diagram import extract  # noqa: E402
from cross_ref import compare  # noqa: E402

KAISER = NLP_ROOT.parent / "data-source-1" / "kaiser_clean.json"
DATA3 = NLP_ROOT.parent / "data-source-3" / "data_source_3_clean.json"


def _by_id(path):
    return {r["id"]: r for r in json.load(open(path))}


def test_airtravel_diagrams_differ():
    """The two references for AirTravel have different relationship arrows
    in the Airline→Airplane edge (kaiser: '--', data_source_3: 'o--')."""
    kaiser = _by_id(KAISER)["AirTravel"]
    data3 = _by_id(DATA3)["AirTravel"]
    d_k = extract(kaiser["puml"])
    d_d = extract(data3["puml"])
    # Sanity: the class sets are the same.
    assert {c["name"] for c in d_k["classes"]} == {c["name"] for c in d_d["classes"]}
    # But the relationship 'Airline→Airplane' differs in type.
    kinds_k = {(r["source"], r["target"], r["type"]) for r in d_k["relationships"]}
    kinds_d = {(r["source"], r["target"], r["type"]) for r in d_d["relationships"]}
    assert kinds_k != kinds_d


def test_cross_ref_runs():
    kaiser = _by_id(KAISER)["BankAccount"]
    data3 = _by_id(DATA3)["BankAccount"]
    d_k = extract(kaiser["puml"])
    d_d = extract(data3["puml"])
    comp = compare(d_k, d_d, "kaiser", "data_source_3")
    assert "jaccard_classes_kaiser_vs_data_source_3" in comp
    # BankAccount classes are identical between the two datasets.
    assert comp["jaccard_classes_kaiser_vs_data_source_3"] == 1.0
