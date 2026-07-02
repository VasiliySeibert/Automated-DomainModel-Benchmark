"""Tests for the dependency-graph binder.

We use a small set of hand-checked sentences whose dep parse is
predictable and we assert the path that the binder reports.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NLP_ROOT = HERE.parent
REPO = NLP_ROOT.parent.parent
for p in (str(REPO), str(NLP_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from dep_match import find_relationship_bindings  # noqa: E402


def test_aircraft_performs_flights():
    """'An aircraft performs several flights.' → aircraft↔flights through 'performs'."""
    rels = [{"source": "Aircraft", "target": "Flight",
             "type": "association", "label": None}]
    out = find_relationship_bindings(rels, "An aircraft performs several flights.")
    assert len(out) == 1
    best = out[0]["best"]
    # We expect the path to go aircraft → performs → flights (2 hops)
    assert best["hop_count"] == 2
    assert best["path_text"].split()[1] in {"performs", "performed"}


def test_no_binding_when_only_one_endpoint_present():
    rels = [{"source": "Aircraft", "target": "Telescope",
             "type": "association", "label": None}]
    out = find_relationship_bindings(rels, "An aircraft performs several flights.")
    assert out == []


def test_bank_consists_of_branches():
    """'A bank consists of any number of branches.' → bank↔branches through 'consists'/'of'."""
    rels = [{"source": "Bank", "target": "Branch",
             "type": "aggregation", "label": None}]
    out = find_relationship_bindings(rels, "A bank consists of any number of branches.")
    assert len(out) == 1
    best = out[0]["best"]
    assert best["hop_count"] >= 2
    # The path should mention at least 'consists' and 'of'
    ptext = best["path_text"].lower()
    assert "consists" in ptext and "of" in ptext
