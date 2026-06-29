"""Tests for Workflow/run_all._resolve_metric — metric.json + CLI precedence."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Import domain_model_metrics BEFORE any Workflow/ file loads (avoids the
# upstream Workflow package shadow issue described in Workflow/README.md).
import domain_model_metrics  # noqa: F401


def _make_candidate(tmp_path: Path, name: str,
                    metric_json: dict | None) -> Path:
    folder = tmp_path / name
    folder.mkdir()
    (folder / "candidate.py").write_text(
        "from Candidates.candidate_interface import CandidateOutput\n"
        "candidate = lambda nlt: CandidateOutput(generated_model='x')\n",
        encoding="utf-8",
    )
    if metric_json is not None:
        (folder / "metric.json").write_text(
            json.dumps(metric_json), encoding="utf-8"
        )
    return folder


def test_cli_metric_overrides_metric_json(tmp_path: Path):
    from Workflow.run_all import _resolve_metric

    folder = _make_candidate(tmp_path, "cand",
                             metric_json={"default_metric": "metrik-2"})
    m, src = _resolve_metric("metrik-3", folder / "candidate.py")
    assert m == "metrik-3"
    assert src == "cli"


def test_metric_json_used_when_no_cli(tmp_path: Path):
    from Workflow.run_all import _resolve_metric

    folder = _make_candidate(tmp_path, "cand",
                             metric_json={"default_metric": "metrik-2"})
    m, src = _resolve_metric(None, folder / "candidate.py")
    assert m == "metrik-2"
    assert src == "candidate_metric.json"


def test_folder_path_resolves_metric_json(tmp_path: Path):
    from Workflow.run_all import _resolve_metric

    folder = _make_candidate(tmp_path, "cand",
                             metric_json={"default_metric": "metrik-5"})
    m, src = _resolve_metric(None, folder)
    assert m == "metrik-5"
    assert src == "candidate_metric.json"


def test_project_default_when_no_cli_or_metric_json(tmp_path: Path):
    from Workflow.run_all import _resolve_metric

    folder = _make_candidate(tmp_path, "cand", metric_json=None)
    m, src = _resolve_metric(None, folder / "candidate.py")
    assert m == "metrik-4"
    assert src == "project_default"


def test_invalid_metric_in_metric_json_rejected(tmp_path: Path):
    from Workflow.run_all import _resolve_metric

    folder = _make_candidate(tmp_path, "cand",
                             metric_json={"default_metric": "metrik-9"})
    with pytest.raises(SystemExit):
        _resolve_metric(None, folder)