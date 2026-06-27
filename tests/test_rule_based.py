"""Tests for the rule-based strategy."""
from __future__ import annotations

import pytest

spacy = pytest.importorskip("spacy")

from Candidates.ai4se_benchmarkPaper.rule_based.strategy import run
from Candidates.registry import get_strategy
from Data.Parser import PlantUMLParser


NLT = (
    "A library has many books. Each book has a title and a year. "
    "Each book is written by exactly one author. An author has a name. "
    "The library has exactly one director."
)


def test_spec_metadata():
    spec = get_strategy("ai4se_benchmarkPaper", "rule_based")
    assert spec is not None
    assert spec.uses_llm is False
    assert spec.source == "ai4se_benchmarkPaper"


def test_rule_based_emits_plantuml():
    spec = get_strategy("ai4se_benchmarkPaper", "rule_based")
    result = run(spec, NLT)
    assert result["failed"] is False
    assert "@startuml" in result["generated_model"]
    assert "@enduml" in result["generated_model"]


def test_rule_based_output_parses():
    parser = PlantUMLParser(strict=False)
    spec = get_strategy("ai4se_benchmarkPaper", "rule_based")
    result = run(spec, NLT)
    model = parser.parse(result["generated_model"])
    assert len(model.classes) >= 1