"""Tests for Workflow/generate.py — step 1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE = REPO_ROOT / "Workflow" / "generate.py"
DUMMY = REPO_ROOT / "Candidates" / "dummy_candidate" / "candidate.py"


def _env():
    return {"PYTHONPATH": str(REPO_ROOT),
            "PATH": "/usr/bin:/bin:/usr/local/bin"}


def _run_generate(tmp_path: Path, *extra: str,
                  dataset: str = "kaiser_clean") -> Path:
    out = tmp_path / f"{dataset}.json"
    cmd = [
        sys.executable, str(GENERATE),
        "--candidate", str(DUMMY),
        "--dataset", dataset,
        "--out", str(out),
        *extra,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, env=_env(), timeout=60)
    assert res.returncode == 0, (
        f"generate.py failed (rc={res.returncode})\n"
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    return out


def test_generate_writes_expected_schema(tmp_path: Path):
    out = _run_generate(tmp_path, "--limit", "3")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["candidate"].endswith("candidate.py")
    assert payload["dataset"] == "kaiser_clean"
    assert payload["n_records"] == 3
    assert payload["n_failed"] == 0
    assert len(payload["records"]) == 3
    for rec in payload["records"]:
        assert {"id", "nlt", "reference", "generated",
                "failed", "error", "raw_excerpt",
                "elapsed_seconds"} <= set(rec)
        assert rec["failed"] is False
        assert "@startuml" in rec["generated"]


def test_generate_accepts_data_source_alias(tmp_path: Path):
    out = _run_generate(tmp_path, "--limit", "2", dataset="data-source-1")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["dataset"] == "data-source-1"
    assert payload["n_records"] == 2


def test_generate_reference_clean(tmp_path: Path):
    out = _run_generate(tmp_path, "--limit", "4", dataset="reference_clean")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["dataset"] == "reference_clean"
    assert payload["n_records"] == 4


def test_generate_idempotent_output(tmp_path: Path):
    out = _run_generate(tmp_path, "--limit", "2")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["records"][0]["generated"] == payload["records"][1]["generated"]


def test_generate_limit_respected(tmp_path: Path):
    out = _run_generate(tmp_path, "--limit", "5")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["n_records"] == 5