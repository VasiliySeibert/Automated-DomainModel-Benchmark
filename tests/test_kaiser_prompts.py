"""Tests for the kaiser prompt files.

Verifies that the prompt files exist, contain the verbatim text from the
upstream `text2uml-kaiser/src/run.py`, and that the `{{` / `}}` brace
escapes have been collapsed to single braces (the LLM needs valid
PlantUML).
"""
from __future__ import annotations

from pathlib import Path

KAISER_DIR = Path(__file__).resolve().parent.parent / "Candidates" / "text2uml-kaiser"


def test_prompt_files_exist():
    expected = {
        "zero_shot": ["prompt.txt"],
        "one_shot":  ["prompt.txt", "examples.json"],
        "few_shot":  ["prompt.txt", "examples.json"],
        "cot":       ["prompt_step1_class.txt", "prompt_step2_assoc.txt",
                      "prompt_step2b_attr.txt", "prompt_step3_card.txt",
                      "prompt_step5_plantuml_system.txt", "prompt_step5_plantuml_user.txt"],
        "cot_domain":["prompt_step1_noun.txt", "prompt_step2_class.txt",
                      "prompt_step3_assoc.txt", "prompt_step2b_attr.txt",
                      "prompt_step5_plantuml_system.txt", "prompt_step5_plantuml_user.txt"],
    }
    for strat, files in expected.items():
        d = KAISER_DIR / strat
        for f in files:
            assert (d / f).is_file(), f"missing {d / f}"


def test_no_double_braces_in_prompts():
    """All prompt_*.txt files must not contain {{ or }} (collapsed)."""
    for txt in KAISER_DIR.glob("*/prompt*.txt"):
        text = txt.read_text(encoding="utf-8")
        assert "{{" not in text, f"{txt} has double braces"
        assert "}}" not in text, f"{txt} has double braces"


def test_zero_shot_prompt_contains_examples():
    text = (KAISER_DIR / "zero_shot" / "prompt.txt").read_text(encoding="utf-8")
    assert "@startuml" in text
    assert 'Book "1..1" -- "1..*" Page' in text


def test_examples_json_well_formed():
    import json
    for ex in ("one_shot/examples.json", "few_shot/examples.json"):
        data = json.loads((KAISER_DIR / ex).read_text(encoding="utf-8"))
        assert "examples" in data
        assert len(data["examples"]) >= 1
        for e in data["examples"]:
            assert {"id", "nlt", "model"} <= set(e.keys())


def test_one_shot_has_alpha_insurance_example():
    import json
    data = json.loads((KAISER_DIR / "one_shot" / "examples.json").read_text(encoding="utf-8"))
    assert data["examples"][0]["id"] == "AlphaInsurance"


def test_few_shot_has_alpha_and_gasstation():
    import json
    data = json.loads((KAISER_DIR / "few_shot" / "examples.json").read_text(encoding="utf-8"))
    ids = [e["id"] for e in data["examples"]]
    assert "AlphaInsurance" in ids
    assert "GasStation" in ids