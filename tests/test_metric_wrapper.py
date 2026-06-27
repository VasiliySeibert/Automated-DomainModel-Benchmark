"""Tests for the Metric wrapper — new bucket boundaries."""
from __future__ import annotations

from Metric import (
    BUCKETS, BUCKET_LABELS, bucketise, compute, summarise,
)


TINY = "@startuml\nclass A {}\nclass B {}\nA -- B\n@enduml"
NEAR = (
    "@startuml\nclass A {}\nclass B {}\nclass C {}\n"
    'A "1" -- "*" B\nA "1" -- "*" C\n@enduml'
)


def test_buckets_constant():
    assert BUCKETS == (0.0, 0.1, 0.2, 0.3, 1.0001)
    assert BUCKET_LABELS == ("[0, 0.1)", "[0.1, 0.2)", "[0.2, 0.3)", "[0.3, 1.0]")


def test_bucketise_boundaries():
    assert bucketise(0.0) == 0
    assert bucketise(0.05) == 0
    assert bucketise(0.099) == 0
    assert bucketise(0.1) == 1
    assert bucketise(0.15) == 1
    assert bucketise(0.199) == 1
    assert bucketise(0.2) == 2
    assert bucketise(0.25) == 2
    assert bucketise(0.299) == 2
    assert bucketise(0.3) == 3
    assert bucketise(0.5) == 3
    assert bucketise(0.9) == 3
    assert bucketise(None) is None


def test_compute_returns_three_scores_in_unit_interval():
    out = compute(TINY, NEAR)
    assert {"class_score", "attribute_score", "association_score",
            "parse_warning_ref", "parse_warning_gen", "error"} <= set(out)
    for k in ("class_score", "attribute_score", "association_score"):
        assert 0.0 <= out[k] <= 1.0


def test_identical_inputs_score_high():
    out = compute(TINY, TINY)
    assert out["class_score"] > 0.5
    assert out["attribute_score"] > 0.5
    assert out["association_score"] > 0.5


def test_disjoint_inputs_score_low():
    out = compute(TINY, "@startuml\nclass X {}\n@enduml")
    assert out["class_score"] < 0.5


def test_summarise_with_new_buckets():
    scores = [
        {"class_score": 0.05, "attribute_score": 0.15, "association_score": 0.35, "error": None},
        {"class_score": 0.15, "attribute_score": 0.25, "association_score": 0.55, "error": None},
        {"class_score": 0.25, "attribute_score": 0.05, "association_score": 0.05, "error": "fail"},
    ]
    summary = summarise(scores)
    # class: [0.05, 0.15, 0.25] -> buckets [0, 1, 2]
    assert summary["class_score"]["buckets"] == [1, 1, 1, 0]
    # attr: [0.15, 0.25, 0.05] -> buckets [1, 2, 0]
    assert summary["attribute_score"]["buckets"] == [1, 1, 1, 0]
    # assoc: [0.35, 0.55, 0.05] -> buckets [3, 3, 0]
    assert summary["association_score"]["buckets"] == [1, 0, 0, 2]
    # failed count
    assert summary["class_score"]["failed"] == 1


def test_compute_handles_empty_generated():
    out = compute(TINY, "")
    assert out["error"] == "empty_generated_model"
    assert out["class_score"] == 0.0