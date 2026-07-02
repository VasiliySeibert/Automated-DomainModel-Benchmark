"""Tests for the lexical matcher (L1..L4 + absent)."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NLP_ROOT = HERE.parent
REPO = NLP_ROOT.parent.parent
for p in (str(REPO), str(NLP_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from lex_match import build_nlt_index, _level_hits  # noqa: E402


NLT_AIRTRAVEL = (
    "The name, type, year of manufacture, and date of the next inspection "
    "are stored for aircraft. An aircraft performs several flights, the "
    "flight number and date of which are stored. Several passengers take "
    "part in a flight, and their names and passport numbers are stored. "
    "A passenger can take part in several flights."
)


def test_l1_direct_hit():
    idx = build_nlt_index(NLT_AIRTRAVEL)
    # 'aircraft' appears verbatim
    res = _level_hits("Aircraft", idx)
    assert res["L1_direct"] is True
    assert res["absent"] is False


def test_plural_lemma_l2():
    # The NLT only has the plural form 'passengers'; we want to check that
    # the matcher recovers the singular class name 'Passenger' via lemma/plural.
    idx = build_nlt_index("Several passengers take part in a flight.")
    res = _level_hits("Passenger", idx)
    # spaCy lemmatises 'passengers' to 'passenger', so L1 already matches.
    # We verify L2 explicitly by checking that the inflect-based plural set
    # also has 'passengers' (the raw NLT form), which is in tokens_lower too.
    assert res["L2_lemma"] is True
    assert res["absent"] is False

    # And the case where the NLT has ONLY 'aircraft' (plural-ish) and the
    # class name is 'Airplane' (no lemma relation without WordNet, and
    # WordNet treats them as different synsets).
    idx2 = build_nlt_index("An aircraft performs several flights.")
    res2 = _level_hits("Airplane", idx2)
    assert res2["L1_direct"] is False
    assert res2["L2_lemma"] is False
    assert res2["L4_synonym"] is False  # different synsets in WordNet
    assert res2["absent"] is True


def test_camelcase_split_l3():
    idx = build_nlt_index(NLT_AIRTRAVEL)
    # 'flightNumber' splits into 'flight' and 'number'. 'flight' and 'number' are in the NLT.
    res = _level_hits("flightNumber", idx)
    assert res["L3_camelcase"] is True
    assert res["absent"] is False


def test_synonym_l4():
    # WordNet links 'bedroom' with 'chamber'. The NLT has 'chamber' only,
    # so 'Bedroom' should be recovered by L4 (synonym) but not L1.
    idx = build_nlt_index("Please sit in the chamber before the meeting.")
    res = _level_hits("Bedroom", idx)
    assert res["L1_direct"] is False
    assert res["L2_lemma"] is False
    assert res["L4_synonym"] is True


def test_absent():
    idx = build_nlt_index("The cat sat on the mat.")
    res = _level_hits("QuantumParticle", idx)
    assert res["absent"] is True
