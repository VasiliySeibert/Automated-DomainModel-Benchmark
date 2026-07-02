"""Tests for the comparison summary JSON.

We run the full pipeline on a small slice (3 records) into a temp
directory, then build the summary JSON and assert its structure.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NLP_ROOT = HERE.parent
REPO = NLP_ROOT.parent.parent
OUT = NLP_ROOT / "out"


@pytest.fixture(scope="module")
def summary_path(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("nlp_test")
    env = {**__import__("os").environ,
           "PYTHONPATH": str(REPO)}
    # 1. analyze.py on a 3-record slice
    subprocess.check_call(
        [sys.executable, str(NLP_ROOT / "analyze.py"),
         "--datasets", "kaiser", "--limit", "3",
         "--out", str(tmp)],
        env=env, cwd=str(REPO))
    # 2. build_summary_json.py
    subprocess.check_call(
        [sys.executable, str(NLP_ROOT / "build_summary_json.py"),
         "--in", str(tmp), "--out", str(tmp)],
        env=env, cwd=str(REPO))
    return tmp / "summary.json"


def test_summary_has_all_keys(summary_path):
    s = json.load(open(summary_path))
    expected = {
        "metadata", "dataset_overview", "relationship_type_counts",
        "cardinality_pattern_counts", "attribute_type_counts",
        "lexical_coverage", "dep_binding", "rel_kind_coverage",
        "nlt_style", "sentence_stats", "parser_warnings",
        "correlation_matrix", "cross_dataset_kaiser_vs_data_source_3",
        "lexically_absent_classes", "records_with_extreme_recoverability",
    }
    assert expected.issubset(set(s.keys())), \
        f"missing keys: {expected - set(s.keys())}"


def test_summary_dataset_overview_counts(summary_path):
    s = json.load(open(summary_path))
    assert "kaiser" in s["dataset_overview"]
    assert s["dataset_overview"]["kaiser"]["n_records"] == 3


def test_summary_rel_counts_match_per_record_csv(summary_path, tmp_path):
    """The sum of relationship-type counts in the JSON should match the
    per-record CSV."""
    import pandas as pd
    s = json.load(open(summary_path))
    tmp = summary_path.parent
    pr = pd.read_csv(tmp / "per_record.csv")
    rel_cols = [c for c in pr.columns if c.startswith("n_rels_")
                and c not in ("n_rels_with_card", "n_rels_with_label",
                              "n_rels_total", "n_rels_bound")]
    csv_total = {c.replace("n_rels_", ""): int(pr[c].sum()) for c in rel_cols}
    json_total = s["relationship_type_counts"]["total"]
    assert json_total == csv_total, \
        f"rel-type mismatch: json={json_total} csv={csv_total}"


def test_summary_cardinality_tuples_valid(summary_path):
    s = json.load(open(summary_path))
    cps = s["cardinality_pattern_counts"]
    for ds, rows in cps.items():
        if ds == "total":
            continue
        for src, tgt, n in rows:
            assert isinstance(src, str)
            assert isinstance(tgt, str)
            assert isinstance(n, int) and n >= 0


def test_summary_jaccard_in_unit_interval(summary_path):
    s = json.load(open(summary_path))
    cr = s["cross_dataset_kaiser_vs_data_source_3"]
    if not cr:
        pytest.skip("no cross-dataset data (only 1 dataset)")
    for col in ("jaccard_classes", "jaccard_attributes", "jaccard_rels"):
        assert 0.0 <= cr[col]["mean"] <= 1.0
        assert 0.0 <= cr[col]["min"] <= 1.0
        assert 0.0 <= cr[col]["max"] <= 1.0


def test_summary_correlation_matrix_is_square(summary_path):
    s = json.load(open(summary_path))
    cm = s["correlation_matrix"]
    cols = cm["columns"]
    assert len(cols) >= 4
    for a in cols:
        assert set(cm["spearman"][a].keys()) == set(cols)


def test_summary_lex_absent_inventory_matches_per_element(summary_path):
    s = json.load(open(summary_path))
    import pandas as pd
    tmp = summary_path.parent
    pe = pd.read_csv(tmp / "per_element_match.csv")
    expected = int(((pe["kind"] == "class") & (pe["absent"])).sum())
    assert s["lexically_absent_classes"]["n_total"] == expected
