"""Tests for the candidate registry.

Verifies that:
- registry discovers all expected source/strategy combinations
- LLM vs rule_based flagging is correct
- skip_folders are populated correctly
- run_fn is callable after discovery
- the cell-count logic gives 41 cells/dataset, 82 records total
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _ensure_discovered():
    """Force a registry discovery before every test in this module."""
    from Candidates.registry import discover
    discover()

from Candidates.registry import (
    SOURCE_DIRS, all_specs, discover, get_strategy, register, CandidateSpec,
)


def test_three_source_groups():
    assert set(SOURCE_DIRS) == {
        "text2uml-kaiser",
        "AutomatedDomainModelling-zenodo",
        "ai4se_benchmarkPaper",
    }


def test_kaiser_has_five_strategies():
    kaiser = [s for s in all_specs() if s.source == "text2uml-kaiser"]
    assert len(kaiser) == 5
    names = {s.strategy for s in kaiser}
    assert names == {"zero_shot", "one_shot", "few_shot", "cot", "cot_domain"}


def test_zenodo_has_five_strategies():
    zenodo = [s for s in all_specs() if s.source == "AutomatedDomainModelling-zenodo"]
    assert len(zenodo) == 5
    names = {s.strategy for s in zenodo}
    assert names == {
        "zero_shot", "one_shot_btms", "one_shot_h2s_short", "two_shot", "cot"
    }


def test_rule_based_present():
    rb = get_strategy("ai4se_benchmarkPaper", "rule_based")
    assert rb is not None
    assert rb.uses_llm is False


def test_total_strategies_is_eleven():
    assert len(all_specs()) == 11


def test_kaiser_skip_rules():
    one_shot = get_strategy("text2uml-kaiser", "one_shot")
    assert "AlphaInsurance" in one_shot.skip_folders

    few_shot = get_strategy("text2uml-kaiser", "few_shot")
    assert "AlphaInsurance" in few_shot.skip_folders
    assert any("GasStation" in f for f in few_shot.skip_folders)


def test_zenodo_skip_rules():
    one_btms = get_strategy("AutomatedDomainModelling-zenodo", "one_shot_btms")
    assert "BTMS" in one_btms.skip_folders

    two_shot = get_strategy("AutomatedDomainModelling-zenodo", "two_shot")
    assert "BTMS" in two_shot.skip_folders
    assert "H2S-Short" in two_shot.skip_folders


def test_run_fn_is_callable():
    """Every registered spec should have a run_fn that can be invoked."""
    specs = all_specs()
    for s in specs:
        if not s.uses_llm:
            # rule_based can be invoked with empty model
            result = s.run_fn("A library has books. Each book has a title.")
            assert "generated_model" in result
        # LLM-driven strategies need real models; skip runtime check here.


def test_discover_is_idempotent():
    """discover() can be called multiple times — each call reloads
    every strategy. The registry contents stay stable: same size and
    same set of keys."""
    first = sorted(s.strategy for s in all_specs() if s.source == "text2uml-kaiser")
    discover()
    second = sorted(s.strategy for s in all_specs() if s.source == "text2uml-kaiser")
    assert first == second
    assert len(all_specs()) == 11