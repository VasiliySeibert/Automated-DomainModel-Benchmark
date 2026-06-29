"""End-to-end test: Workflow/run_all.py produces the full output tree."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_ALL = REPO_ROOT / "Workflow" / "run_all.py"
DUMMY = REPO_ROOT / "Candidates" / "dummy_candidate" / "candidate.py"


def _env():
    return {"PYTHONPATH": str(REPO_ROOT),
            "PATH": "/usr/bin:/bin:/usr/local/bin"}


def test_run_all_end_to_end(tmp_path: Path):
    results_dir = tmp_path / "dummy"
    out_dir = tmp_path / "agg"
    res = subprocess.run([
        sys.executable, str(RUN_ALL),
        "--candidate", str(DUMMY),
        "--dataset", "kaiser_clean",
        "--limit", "3",
        "--results-dir", str(results_dir),
        "--out-dir", str(out_dir),
    ], capture_output=True, text=True, env=_env(), timeout=120)
    assert res.returncode == 0, (
        f"run_all failed (rc={res.returncode})\n"
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )

    raw = results_dir / "kaiser_clean.json"
    assert raw.exists()
    scored = results_dir / "kaiser_clean_scored.json"
    assert scored.exists()
    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["metric_name"] == "metrik-1"

    assert (out_dir / "_summary.csv").exists()
    assert (out_dir / "_bucket_kaiser_clean_class_score_metrik-1.csv").exists()
    assert (out_dir / "_bucket_kaiser_clean_attribute_score_metrik-1.csv").exists()
    assert (out_dir / "_bucket_kaiser_clean_association_score_metrik-1.csv").exists()
    assert (out_dir / "_errors.csv").exists()


def test_run_all_dummy_default_metric_is_metrik_1(tmp_path: Path):
    """No --metric on the CLI; metric.json supplies metrik-1."""
    results_dir = tmp_path / "dummy"
    out_dir = tmp_path / "agg"
    res = subprocess.run([
        sys.executable, str(RUN_ALL),
        "--candidate", str(DUMMY),
        "--dataset", "reference_clean",
        "--limit", "2",
        "--results-dir", str(results_dir),
        "--out-dir", str(out_dir),
        "--skip-visualise",
    ], capture_output=True, text=True, env=_env(), timeout=120)
    assert res.returncode == 0, res.stderr
    scored = results_dir / "reference_clean_scored.json"
    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["metric_name"] == "metrik-1"


def test_run_all_metric_flag_overrides_metric_json(tmp_path: Path):
    results_dir = tmp_path / "dummy"
    out_dir = tmp_path / "agg"
    res = subprocess.run([
        sys.executable, str(RUN_ALL),
        "--candidate", str(DUMMY),
        "--dataset", "reference_clean",
        "--limit", "2",
        "--metric", "metrik-4",
        "--results-dir", str(results_dir),
        "--out-dir", str(out_dir),
        "--skip-visualise",
    ], capture_output=True, text=True, env=_env(), timeout=120)
    assert res.returncode == 0, res.stderr
    scored = results_dir / "reference_clean_scored.json"
    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["metric_name"] == "metrik-4"


def test_run_all_metric_appears_in_banner(tmp_path: Path):
    results_dir = tmp_path / "dummy"
    res = subprocess.run([
        sys.executable, str(RUN_ALL),
        "--candidate", str(DUMMY),
        "--dataset", "kaiser_clean",
        "--limit", "1",
        "--results-dir", str(results_dir),
        "--out-dir", str(tmp_path / "agg"),
        "--skip-visualise",
    ], capture_output=True, text=True, env=_env(), timeout=120)
    assert res.returncode == 0, res.stderr
    assert "Metric" in res.stdout
    assert "metrik-1" in res.stdout


def test_run_all_rejects_invalid_metric(tmp_path: Path):
    results_dir = tmp_path / "dummy"
    res = subprocess.run([
        sys.executable, str(RUN_ALL),
        "--candidate", str(DUMMY),
        "--dataset", "kaiser_clean",
        "--limit", "1",
        "--metric", "metrik-9",
        "--results-dir", str(results_dir),
        "--out-dir", str(tmp_path / "agg"),
        "--skip-visualise",
    ], capture_output=True, text=True, env=_env(), timeout=120)
    assert res.returncode != 0