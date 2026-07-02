"""Smoke test for `Candidates/rule_based/run.py`.

Runs the per-candidate driver end-to-end on the first three records of
`kaiser_clean` with the collector skipped. The test passes if the driver
exits 0 and the resulting `_scored.json` is well-formed and contains
non-failed records with metric scores.

Skipped when `spacy` (or the `en_core_web_sm` model) is not installed;
the candidate itself records every record as `failed=True` in that
case and we don't want CI to be red for an environment issue.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent


def _spacy_available() -> bool:
    try:
        import spacy  # noqa: F401
    except Exception:
        return False
    try:
        import spacy

        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _spacy_available(),
    reason="spacy / en_core_web_sm not installed in this environment",
)


def test_run_py_smoke(tmp_path: Path) -> None:
    out_dir = tmp_path / "results"
    proc = subprocess.run(
        [
            sys.executable,
            "Candidates/rule_based/run.py",
            "--dataset", "kaiser_clean",
            "--results-dir", str(out_dir),
            "--out-dir", str(out_dir),
            "--limit", "3",
            "--skip-collect",
        ],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (
        f"run.py exited {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )

    scored = out_dir / "kaiser_clean_scored.json"
    assert scored.is_file(), f"missing scored JSON: {scored}"

    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["dataset"] == "kaiser_clean"
    assert payload["n_records"] == 3
    assert payload["metric_name"] == "metrik-1"
    assert len(payload["records"]) == 3

    for rec in payload["records"]:
        assert "scores" in rec, f"record {rec['id']!r} missing scores block"
        scores = rec["scores"]
        assert "class_score" in scores
        assert "attribute_score" in scores
        assert "association_score" in scores

    raw = out_dir / "kaiser_clean.json"
    assert raw.is_file(), f"missing raw JSON: {raw}"


def test_run_py_metric_override(tmp_path: Path) -> None:
    """Confirm `--metric` overrides the candidate's metric.json."""
    out_dir = tmp_path / "results"
    proc = subprocess.run(
        [
            sys.executable,
            "Candidates/rule_based/run.py",
            "--dataset", "kaiser_clean",
            "--results-dir", str(out_dir),
            "--out-dir", str(out_dir),
            "--limit", "1",
            "--metric", "metrik-4",
            "--skip-collect",
        ],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (
        f"run.py exited {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )

    scored = out_dir / "kaiser_clean_scored.json"
    payload = json.loads(scored.read_text(encoding="utf-8"))
    assert payload["metric_name"] == "metrik-4"


def test_generated_parses_under_strict_metric(tmp_path: Path) -> None:
    """Regression: every generated record must score cleanly under
    `metrik-4` (which uses the upstream PlantUMLParser in strict mode).

    Previously failed on `HotelBookingManagementSystem` (`i.e. <|-- Booking`)
    and `eHome2020` (`- "1" o-- "1" Set`); the fix filters such
    non-identifier tokens out of the class pool and drops malformed
    relationship lines via `_sanitise_body`.
    """
    # In-process so we can drive the workflow's wrapper.compute() with
    # metrik-4 directly without spawning a subprocess.
    from Candidates.rule_based.candidate import candidate as _candidate
    from Metric.wrapper import compute

    import json as _json
    ds_path = REPO / "Data" / "data-source-1" / "kaiser_clean.json"
    records = _json.loads(ds_path.read_text(encoding="utf-8"))

    failures: list[tuple[str, str]] = []
    for rec in records:
        out = _candidate(rec["nlt"])
        result = compute(rec["puml"], out.generated_model, metric_name="metrik-4")
        if result.get("error"):
            first_line = result["error"].split("\n", 1)[0]
            failures.append((rec["id"], first_line))

    assert not failures, (
        "metrik-4 strict parse failed on:\n"
        + "\n".join(f"  {rid}: {err}" for rid, err in failures)
    )