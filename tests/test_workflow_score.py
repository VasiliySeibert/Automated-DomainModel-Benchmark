"""Tests for Workflow/score.py — step 2."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE = REPO_ROOT / "Workflow" / "generate.py"
SCORE = REPO_ROOT / "Workflow" / "score.py"
DUMMY = REPO_ROOT / "Candidates" / "dummy_candidate" / "candidate.py"


def _env():
    return {"PYTHONPATH": str(REPO_ROOT),
            "PATH": "/usr/bin:/bin:/usr/local/bin"}


def _gen(tmp_path: Path, limit: int = 2) -> Path:
    raw = tmp_path / "kaiser_clean.json"
    subprocess.run([
        sys.executable, str(GENERATE),
        "--candidate", str(DUMMY),
        "--dataset", "kaiser_clean",
        "--out", str(raw),
        "--limit", str(limit),
    ], check=True, env=_env(), timeout=60)
    return raw


def _gen_and_score(tmp_path: Path, limit: int = 2, metric: str = "metrik-4"):
    raw = _gen(tmp_path, limit=limit)
    subprocess.run([
        sys.executable, str(SCORE),
        "--in", str(raw),
        "--metric", metric,
    ], check=True, env=_env(), timeout=60)
    return raw, raw.with_name(raw.stem + "_scored.json")


def test_score_appends_scores_to_each_record(tmp_path: Path):
    _, scored = _gen_and_score(tmp_path, limit=2)
    payload = json.loads(scored.read_text(encoding="utf-8"))
    for rec in payload["records"]:
        s = rec["scores"]
        assert {"class_score", "attribute_score", "association_score",
                "parse_warning_ref", "parse_warning_gen", "error"} <= set(s)


def test_score_adds_summary_and_metric_name(tmp_path: Path):
    _, scored = _gen_and_score(tmp_path, limit=2)
    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["metric_name"] == "metrik-4"
    assert "summary" in payload
    for el in ("class_score", "attribute_score", "association_score"):
        s = payload["summary"][el]
        assert {"mean", "std", "median", "mad", "n",
                "buckets", "failed"} <= set(s)
        assert len(s["buckets"]) == 4


def test_score_writes_scored_file_next_to_input(tmp_path: Path):
    raw, scored = _gen_and_score(tmp_path, limit=2)
    assert scored.exists()
    assert scored.parent == raw.parent


def test_score_accepts_metric_flag_metrik_1(tmp_path: Path):
    _, scored = _gen_and_score(tmp_path, limit=2, metric="metrik-1")
    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["metric_name"] == "metrik-1"


def test_score_accepts_metric_flag_metrik_5(tmp_path: Path):
    _, scored = _gen_and_score(tmp_path, limit=2, metric="metrik-5")
    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["metric_name"] == "metrik-5"


def test_score_rejects_invalid_metric(tmp_path: Path):
    raw = _gen(tmp_path, limit=2)
    res = subprocess.run([
        sys.executable, str(SCORE),
        "--in", str(raw),
        "--metric", "metrik-9",
    ], capture_output=True, text=True, env=_env(), timeout=60)
    assert res.returncode != 0
    assert "metrik-9" in res.stderr or "metrik-9" in res.stdout