"""Tests for the zenodo prompt files."""
from __future__ import annotations

import json
from pathlib import Path

ZENODO_DIR = (
    Path(__file__).resolve().parent.parent
    / "Candidates" / "AutomatedDomainModelling_zenodo"
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
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )

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
    out = text_to_plantuml(sample)
    assert out is not None
    assert "enum Shift" in out
    assert "Bus --|> Vehicle" in out
    assert 'BTMS "1" *-- "*" BusVehicle' in out


def test_text_to_plantuml_returns_none_for_unrelated_text():
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )
    assert text_to_plantuml("just a random paragraph") is None


def test_text_to_plantuml_btms_round_trip():
    """The BTMS example must produce PlantUML that Data.Parser accepts."""
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )
    from Data.Parser.parser import PlantUMLParser

    sample = """
Enumeration:
Shift(morning, afternoon, night)
Classes:
BTMS()
BusVehicle(string licencePlate, boolean inRepairShop)
Route(int number)
RouteAssignment(Date date)
Driver(string name, string id, boolean onSickLeave)

Relationships:
1 BTMS contain * BusVehicle
1 BTMS contain * Route
1 BTMS contain * RouteAssignment
* RouteAssignment associate 1 BusVehicle
* RouteAssignment associate 1 Route
"""
    out = text_to_plantuml(sample)
    assert out is not None
    model = PlantUMLParser(strict=False).parse(out)
    assert model.summary().startswith("ParsedModel: 5 classes, 1 enums, 5 relationships")


def test_text_to_plantuml_handles_isA_verb():
    """`isA` (used in the CoT H2S annotated example) must be converted."""
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )

    sample = """
Classes:
Parent()
Child()
Relationships:
Child isA Parent
"""
    out = text_to_plantuml(sample)
    assert out is not None
    assert "Child --|> Parent" in out


def test_text_to_plantuml_handles_plural_headers():
    """`Enumerations:` and `Classes:` (plural) must also work."""
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )

    sample = """
Enumerations:
Color(red, green, blue)
Classes:
Foo()
Bar()
Relationships:
1 Foo associate * Bar
"""
    out = text_to_plantuml(sample)
    assert out is not None
    assert "enum Color" in out
    assert "Foo " in out
    assert "Bar" in out


def test_text_to_plantuml_handles_markdown_fences():
    """LLMs sometimes wrap their answer in triple-backtick fences."""
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )

    sample = """```
Enumeration:
Status(active, inactive)
Classes:
Account(string name)
Relationships:
1 Account associate * Account
```"""
    out = text_to_plantuml(sample)
    assert out is not None
    assert "enum Status" in out


def test_text_to_plantuml_handles_leading_prose():
    """LLMs sometimes preface their answer with prose before the structure."""
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )

    sample = """Sure, here is the class diagram:

Enumeration:
Type(a, b)
Classes:
Foo()
Bar()
Relationships:
1 Foo associate * Bar
"""
    out = text_to_plantuml(sample)
    assert out is not None
    assert "enum Type" in out
    assert "Foo " in out


def test_text_to_plantuml_quotes_cardinalities():
    """All emitted cardinalities must be quoted (parser accepts both, but
    the kaiser step-5 convention is quoted)."""
    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
        text_to_plantuml,
    )

    sample = """
Classes:
Foo()
Bar()
Relationships:
1 Foo associate * Bar
"""
    out = text_to_plantuml(sample)
    assert out is not None
    assert 'Foo "1" -- "*" Bar' in out


def test_zenodo_strategies_carry_temperature_and_num_predict():
    """All 5 zenodo strategies must declare upstream's temperature/num_predict."""
    from Candidates.registry import all_specs

    zenodo = [s for s in all_specs() if s.source == "AutomatedDomainModelling_zenodo"]
    assert len(zenodo) == 5
    for s in zenodo:
        assert s.temperature == 0.7, f"{s.strategy}: temperature={s.temperature}"
        assert s.num_predict == 1024, f"{s.strategy}: num_predict={s.num_predict}"


def test_messages_flatten_splits_system_from_user():
    """`_messages.flatten` must return the first message as `system`
    and concatenate the rest as a single `user` string with role labels."""
    from Candidates.AutomatedDomainModelling_zenodo._messages import flatten

    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user",   "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user",   "content": "u2"},
    ]
    system, user = flatten(msgs)
    assert system == "sys"
    assert "USER:" in user
    assert "ASSISTANT:" in user
    assert "u1" in user
    assert "a1" in user
    assert "u2" in user
    # system must appear before the first user label
    assert user.index("USER:") < user.index("ASSISTANT:")
    assert user.index("ASSISTANT:") < user.rindex("USER:")


def test_messages_flatten_handles_empty_list():
    from Candidates.AutomatedDomainModelling_zenodo._messages import flatten
    assert flatten([]) == ("", "")
    # A list with no system message is treated as user-only and rendered
    # with role labels (mirrors the multi-turn case).
    assert flatten([{"role": "user", "content": "x"}]) == ("", "USER:\nx")