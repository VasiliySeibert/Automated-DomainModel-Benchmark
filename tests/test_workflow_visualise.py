"""Tests for Workflow/visualise.py — step 3."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE = REPO_ROOT / "Workflow" / "generate.py"
SCORE = REPO_ROOT / "Workflow" / "score.py"
VISUALISE = REPO_ROOT / "Workflow" / "visualise.py"
DUMMY = REPO_ROOT / "Candidates" / "dummy_candidate" / "candidate.py"


def _env():
    return {"PYTHONPATH": str(REPO_ROOT),
            "PATH": "/usr/bin:/bin:/usr/local/bin"}


def _full_pipeline(tmp_path: Path, dataset: str = "kaiser_clean", limit: int = 2,
                   metric: str = "metrik-4"):
    raw = tmp_path / f"{dataset}.json"
    subprocess.run([
        sys.executable, str(GENERATE),
        "--candidate", str(DUMMY),
        "--dataset", dataset,
        "--out", str(raw),
        "--limit", str(limit),
    ], check=True, env=_env(), timeout=60)
    subprocess.run([
        sys.executable, str(SCORE),
        "--in", str(raw),
        "--metric", metric,
    ], check=True, env=_env(), timeout=60)
    return raw.with_name(raw.stem + "_scored.json")


def test_visualise_requires_metric_flag(tmp_path: Path):
    scored = _full_pipeline(tmp_path, dataset="kaiser_clean", limit=2)
    out_dir = tmp_path / "agg"
    res = subprocess.run([
        sys.executable, str(VISUALISE),
        "--in", str(scored),
        "--out-dir", str(out_dir),
    ], capture_output=True, text=True, env=_env(), timeout=60)
    assert res.returncode != 0
    assert "--metric" in res.stderr


def test_visualise_writes_bucket_summary_errors(tmp_path: Path):
    scored = _full_pipeline(tmp_path, dataset="kaiser_clean", limit=3,
                            metric="metrik-1")
    out_dir = tmp_path / "agg"
    subprocess.run([
        sys.executable, str(VISUALISE),
        "--in", str(scored),
        "--out-dir", str(out_dir),
        "--metric", "metrik-1",
    ], check=True, env=_env(), timeout=60)

    assert (out_dir / "_summary.csv").exists()
    assert (out_dir / "_summary.json").exists()
    assert (out_dir / "_errors.csv").exists()
    for el in ("class_score", "attribute_score", "association_score"):
        assert (out_dir / f"_bucket_kaiser_clean_{el}_metrik-1.csv").exists()


def test_visualise_writes_heatmap_pngs(tmp_path: Path):
    scored = _full_pipeline(tmp_path, dataset="reference_clean", limit=3,
                            metric="metrik-1")
    out_dir = tmp_path / "agg"
    subprocess.run([
        sys.executable, str(VISUALISE),
        "--in", str(scored),
        "--out-dir", str(out_dir),
        "--metric", "metrik-1",
    ], check=True, env=_env(), timeout=60)
    pngs = list(out_dir.glob("heatmap_reference_clean_*_metrik-1.png"))
    assert len(pngs) == 3


def test_visualise_summary_csv_columns(tmp_path: Path):
    scored = _full_pipeline(tmp_path, dataset="kaiser_clean", limit=2,
                            metric="metrik-1")
    out_dir = tmp_path / "agg"
    subprocess.run([
        sys.executable, str(VISUALISE),
        "--in", str(scored),
        "--out-dir", str(out_dir),
        "--metric", "metrik-1",
    ], check=True, env=_env(), timeout=60)
    summary_csv = (out_dir / "_summary.csv").read_text(encoding="utf-8")
    header = summary_csv.splitlines()[0]
    assert "metric" in header
    for col in ("metric", "candidate", "dataset", "element", "n", "n_failed",
                "mean", "median", "bucket_0_0.1", "bucket_0.1_0.2",
                "bucket_0.2_0.3", "bucket_0.3_1.0"):
        assert col in header


def test_visualise_summary_csv_metric_value(tmp_path: Path):
    scored = _full_pipeline(tmp_path, dataset="kaiser_clean", limit=2,
                            metric="metrik-4")
    out_dir = tmp_path / "agg"
    subprocess.run([
        sys.executable, str(VISUALISE),
        "--in", str(scored),
        "--out-dir", str(out_dir),
        "--metric", "metrik-4",
    ], check=True, env=_env(), timeout=60)
    summary_csv = (out_dir / "_summary.csv").read_text(encoding="utf-8")
    body = summary_csv.splitlines()[1:]
    assert len(body) >= 1
    # metric is the first column
    assert all(line.startswith("metrik-4,") for line in body)


def test_visualise_accepts_glob(tmp_path: Path):
    scored = _full_pipeline(tmp_path, dataset="kaiser_clean", limit=2,
                            metric="metrik-1")
    out_dir = tmp_path / "agg"
    subprocess.run([
        sys.executable, str(VISUALISE),
        "--in", str(scored.parent / "*_scored.json"),
        "--out-dir", str(out_dir),
        "--metric", "metrik-1",
    ], check=True, env=_env(), timeout=60)
    assert (out_dir / "_bucket_kaiser_clean_class_score_metrik-1.csv").exists()


def test_visualise_rejects_mixed_metric_inputs(tmp_path: Path):
    a = _full_pipeline(tmp_path / "a", dataset="kaiser_clean", limit=2,
                       metric="metrik-1")
    b = _full_pipeline(tmp_path / "b", dataset="reference_clean", limit=2,
                       metric="metrik-4")
    out_dir = tmp_path / "agg"
    res = subprocess.run([
        sys.executable, str(VISUALISE),
        "--in", str(a),
        "--in", str(b),
        "--out-dir", str(out_dir),
        "--metric", "metrik-1",
    ], capture_output=True, text=True, env=_env(), timeout=60)
    assert res.returncode != 0
    assert "metrik-4" in res.stderr