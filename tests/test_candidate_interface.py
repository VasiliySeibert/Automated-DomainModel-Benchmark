"""Tests for the `Candidate` interface and the dummy candidate."""
from __future__ import annotations

from pathlib import Path

import pytest

from Candidates.candidate_interface import (
    Candidate,
    CandidateOutput,
    load_candidate,
)
from Candidates.dummy_candidate.candidate import DummyCandidate, candidate


REPO_ROOT = Path(__file__).resolve().parent.parent
DUMMY_PATH = REPO_ROOT / "Candidates" / "dummy_candidate" / "candidate.py"
DUMMY_DIR = REPO_ROOT / "Candidates" / "dummy_candidate"


# ── CandidateOutput ──────────────────────────────────────────────────────────


def test_candidate_output_as_dict_keys():
    out = CandidateOutput(
        generated_model="PUML",
        failed=False,
        error=None,
        raw_excerpt="PUML",
    )
    assert set(out.as_dict()) == {
        "generated_model", "failed", "error", "raw_excerpt"
    }


def test_candidate_output_from_dict_round_trip():
    src = {
        "generated_model": "x", "failed": True,
        "error": "boom", "raw_excerpt": "abc",
    }
    out = CandidateOutput.from_dict(src)
    assert out.generated_model == "x"
    assert out.failed is True
    assert out.error == "boom"
    assert out.raw_excerpt == "abc"


def test_candidate_output_defaults():
    out = CandidateOutput()
    assert out.generated_model == ""
    assert out.failed is False
    assert out.error is None
    assert out.raw_excerpt == ""


# ── DummyCandidate ───────────────────────────────────────────────────────────


def test_dummy_returns_constant_puml():
    c = DummyCandidate()
    a = c("anything goes here")
    b = c("a completely different NLT")
    assert a.generated_model == b.generated_model
    assert "@startuml" in a.generated_model
    assert "@enduml" in a.generated_model


def test_dummy_never_fails():
    c = DummyCandidate()
    out = c("")
    assert out.failed is False
    assert out.error is None


def test_dummy_module_level_candidate_is_a_candidate():
    assert isinstance(candidate, Candidate)


def test_dummy_conforms_to_candidate_protocol():
    assert isinstance(DummyCandidate(), Candidate)


# ── load_candidate ───────────────────────────────────────────────────────────


def test_load_candidate_from_file_path():
    c = load_candidate(DUMMY_PATH)
    assert isinstance(c, Candidate)
    out = c("anything")
    assert out.failed is False


def test_load_candidate_from_folder_path():
    c = load_candidate(DUMMY_DIR)
    assert isinstance(c, Candidate)
    out = c("anything")
    assert "@startuml" in out.generated_model


def test_load_candidate_missing_path_raises(tmp_path: Path):
    bogus = tmp_path / "does_not_exist.py"
    with pytest.raises(FileNotFoundError):
        load_candidate(bogus)


def test_load_candidate_missing_candidate_attribute(tmp_path: Path):
    bad = tmp_path / "candidate.py"
    bad.write_text("# nothing here\n", encoding="utf-8")
    with pytest.raises(AttributeError):
        load_candidate(bad)


def test_load_candidate_not_callable(tmp_path: Path):
    bad = tmp_path / "candidate.py"
    bad.write_text("candidate = 42\n", encoding="utf-8")
    with pytest.raises(TypeError):
        load_candidate(bad)