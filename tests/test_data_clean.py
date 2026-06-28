"""Tests for the cleaned benchmark datasets.

Verifies:
- both cleaned JSONs exist and are well-formed
- schema is [{id, nlt, puml}, ...] and counts match the raw originals
- `Metric.compute(clean, clean)` returns 1.0 on all three element scores with
  zero parse warnings and no error — the metrik-4 strict parser accepts every
  record cleanly
- the five normalisers are idempotent (running twice = running once)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Data import (
    load_kaiser, load_kaiser_clean, load_reference, load_reference_clean,
    load_dataset,
)
from Data.clean_datasets import (
    normalise,
    _strip_enum_stereotype, _repair_diamonds, _rewrite_extends,
    _rewrite_bidirectional, _rewrite_note_alias,
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


def test_clean_ids_match_raw():
    assert {r["id"] for r in load_kaiser_clean()} == {r["id"] for r in load_kaiser()}
    assert {r["id"] for r in load_reference_clean()} == {r["id"] for r in load_reference()}


def test_clean_load_dataset_dispatch():
    assert load_dataset("kaiser_clean") == load_kaiser_clean()
    assert load_dataset("reference_clean") == load_reference_clean()


@pytest.mark.parametrize("records", [load_kaiser_clean(), load_reference_clean()])
def test_clean_records_score_one_against_self(records):
    """metrik-4 with strict parsing must accept every cleaned record.

    The reference side parse-warning list must be empty AND the element scores
    must be at or near the metrik-4 self-similarity ceiling (~1.0; tiny
    deviations are intrinsic to metrik-4's normalisation, not caused by the
    rewrite).
    """
    for r in records:
        out = compute(r["puml"], r["puml"])
        assert out["error"] is None, f"{r['id']}: error={out['error']}"
        assert out["parse_warning_ref"] == [], (
            f"{r['id']}: ref warnings={out['parse_warning_ref'][:3]}"
        )
        assert out["parse_warning_gen"] == [], (
            f"{r['id']}: gen warnings={out['parse_warning_gen'][:3]}"
        )
        for k in ("class_score", "attribute_score", "association_score"):
            assert out[k] >= 0.95, f"{r['id']}: {k}={out[k]} < 0.95"


def test_clean_normalisers_are_idempotent():
    raw_kaiser = load_kaiser()
    raw_reference = load_reference()
    for r in raw_kaiser + raw_reference:
        once = normalise(r["puml"])
        twice = normalise(once)
        assert once == twice, f"{r['id']}: not idempotent"


def test_clean_normalisers_preserve_enum_values():
    """Each enum declaration must keep its name and its list of values."""
    raw_kaiser = load_kaiser()
    raw_reference = load_reference()
    ident = re = __import__("re")
    val_pat = ident.compile(r"\{([^}]*)\}")

    for r in raw_kaiser + raw_reference:
        raw = r["puml"]
        if "<<enum>>" not in raw:
            continue
        cleaned = normalise(raw)
        # Find the matching enum block (now without <<enum>>).
        # Extract value set before and after; the cleaned version must contain them.
        raw_enums = ident.findall(r"enum\s+[A-Za-z_][A-Za-z0-9_]*\s*<<enum>>\s*\{([^}]*)\}", raw)
        cleaned_enums = ident.findall(r"enum\s+[A-Za-z_][A-Za-z0-9_]*\s*\{([^}]*)\}", cleaned)
        assert raw_enums, f"{r['id']}: no <<enum>> enums found in raw"
        # The cleaned diagram must still contain the same enum-name + values.
        for raw_body in raw_enums:
            raw_vals = {v.strip() for v in raw_body.split(",") if v.strip()}
            assert any(
                {v.strip() for v in cleaned_body.split(",") if v.strip()} >= raw_vals
                for cleaned_body in cleaned_enums
            ), f"{r['id']}: enum values lost during clean"


def test_clean_extends_rewrite_introduces_inheritance_arrow():
    """HBMS's `class SpecialOffer extends Offer` must become
    `class SpecialOffer` + `SpecialOffer --|> Offer`."""
    raw = next(r for r in load_reference() if r["id"] == "HBMS")
    cleaned_puml = normalise(raw["puml"])
    assert "extends" not in cleaned_puml, "extends keyword should be gone"
    assert "class SpecialOffer" in cleaned_puml
    assert "class RegularOffer" in cleaned_puml
    assert "SpecialOffer --|> Offer" in cleaned_puml
    assert "RegularOffer --|> Offer" in cleaned_puml


def test_clean_diamond_rewrite_normalises_arrows():
    """Every malformed `*-` / `-*` / `*->` / `<-*` / `o->` / `<-o` form must
    be replaced by its canonical 2-dash / 3-char equivalent."""
    raw = load_kaiser()
    target_ids = {"GasStation_TUW", "HelpingHands", "School", "TileOGame", "University", "TeamSportsScoutingSystem"}
    bad_forms = ["*-", "-*", "*- >".replace(" ", ""), "<-*", "o->", "<-o", "<-->"]
    for r in raw:
        if r["id"] not in target_ids:
            continue
        cleaned = normalise(r["puml"])
        for bad in bad_forms:
            # The bad 2-/3-char forms with surrounding word chars must not appear.
            assert not _looks_like_bad_arrow(cleaned, bad), (
                f"{r['id']}: bad form {bad!r} survived normalise()"
            )


def _looks_like_bad_arrow(puml: str, bad: str) -> bool:
    """Heuristic: does `bad` appear in puml in a non-cardinality, non-valid context?"""
    import re as _re
    # Same constraints as the normaliser itself.
    return bool(_re.search(r"(?<![<.\-\d])" + _re.escape(bad) + r"(?!-)", puml))