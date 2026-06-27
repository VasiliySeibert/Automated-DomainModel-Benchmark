"""Tests for the zenodo prompt files."""
from __future__ import annotations

import json
from pathlib import Path

ZENODO_DIR = (
    Path(__file__).resolve().parent.parent
    / "Candidates" / "AutomatedDomainModelling-zenodo"
)


def test_prompt_files_exist():
    expected = {
        "zero_shot":         ["prompt_system.txt", "prompt_task.txt"],
        "one_shot_btms":     ["prompt_system.txt", "prompt_task.txt", "examples.json"],
        "one_shot_h2s_short":["prompt_system.txt", "prompt_task.txt", "examples.json"],
        "two_shot":          ["prompt_system.txt", "prompt_task.txt", "examples.json"],
        "cot":               ["prompt_system.txt", "prompt_task.txt", "annotated_example.txt"],
    }
    for strat, files in expected.items():
        d = ZENODO_DIR / strat
        for f in files:
            assert (d / f).is_file(), f"missing {d / f}"


def test_examples_json_well_formed():
    for ex in ("one_shot_btms/examples.json",
               "one_shot_h2s_short/examples.json",
               "two_shot/examples.json"):
        data = json.loads((ZENODO_DIR / ex).read_text(encoding="utf-8"))
        assert "examples" in data
        for e in data["examples"]:
            assert {"id", "nlt", "model"} <= set(e.keys())


def test_two_shot_has_both_examples():
    data = json.loads((ZENODO_DIR / "two_shot" / "examples.json").read_text(encoding="utf-8"))
    ids = {e["id"] for e in data["examples"]}
    assert "BTMS" in ids
    assert "H2S-Short" in ids


def test_cot_has_annotated_example():
    text = (ZENODO_DIR / "cot" / "annotated_example.txt").read_text(encoding="utf-8")
    # The annotated example has "->" arrows linking sentences to inferences.
    assert "->" in text
    assert "H2S" in text


def test_text_to_plantuml_converter_basic():
    """Inline test of the source-group-shared converter."""
    # Use importlib because the folder name has a hyphen.
    import importlib.util, sys
    p = ZENODO_DIR / "zenodo_text_format.py"
    spec = importlib.util.spec_from_file_location("ztf", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ztf"] = mod
    spec.loader.exec_module(mod)

    sample = """
Enumeration:
Shift(morning, afternoon, night)
Classes:
BTMS()
BusVehicle(string licencePlate, boolean inRepairShop)
Relationships:
1 BTMS contain * BusVehicle
Bus inherit Vehicle
"""
    out = mod.text_to_plantuml(sample)
    assert out is not None
    assert "enum Shift" in out
    assert "Bus --|> Vehicle" in out
    assert 'BTMS "1" *-- "*" BusVehicle' in out


def test_text_to_plantuml_returns_none_for_unrelated_text():
    import importlib.util, sys
    p = ZENODO_DIR / "zenodo_text_format.py"
    spec = importlib.util.spec_from_file_location("ztf", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ztf"] = mod
    spec.loader.exec_module(mod)
    assert mod.text_to_plantuml("just a random paragraph") is None