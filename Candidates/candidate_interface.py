"""Candidate interface — what every workflow candidate must implement.

A Candidate is a callable that takes a natural-language specification
(`nlt`) and returns a `CandidateOutput` containing a PlantUML string.

The workflow calls a Candidate once per record, persists the raw
output, scores it in a separate step, and visualises the results.
The workflow itself has no candidate-specific knowledge — model
selection, prompt construction, and response parsing are the
candidate's responsibility.

The canonical (and currently only) implementation is the dummy in
`Candidates/dummy_candidate/candidate.py`. Real LLM-driven
candidates (one_shot, CoT, rule-based, …) will be migrated to this
interface in a follow-up step.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable


# ─── Public types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CandidateInput:
    """What the workflow hands to a candidate.

    `nlt`       — the natural-language specification text.
    `record_id` — opaque identifier for logging only. Candidates MUST
                  NOT branch on it (branching would defeat the benchmark).
    """
    nlt: str
    record_id: str = ""


@dataclass
class CandidateOutput:
    """Standardised response envelope.

    `failed=True` short-circuits the scorer (all three metrik-4 element
    scores become 0.0 and the record appears in `_errors.csv`).
    """
    generated_model: str = ""
    failed: bool = False
    error: Optional[str] = None
    raw_excerpt: str = ""

    def as_dict(self) -> dict:
        return {
            "generated_model": self.generated_model,
            "failed":          self.failed,
            "error":           self.error,
            "raw_excerpt":     self.raw_excerpt,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CandidateOutput":
        return cls(
            generated_model=d.get("generated_model", ""),
            failed=bool(d.get("failed", False)),
            error=d.get("error"),
            raw_excerpt=d.get("raw_excerpt", ""),
        )


@runtime_checkable
class Candidate(Protocol):
    """The contract every workflow candidate must satisfy.

    Implementations may be classes (with `__call__`) or plain functions.
    The workflow only requires that the object is callable with one
    positional `nlt` argument and returns an object exposing the four
    `CandidateOutput` attributes.
    """
    def __call__(self, nlt: str) -> CandidateOutput: ...


# ─── Loader ──────────────────────────────────────────────────────────────────


def load_candidate(path: str | Path) -> Candidate:
    """Load a candidate from a filesystem path.

    Accepts either:
      * a path to a Python file (`.../candidate.py`) — exposes a
        module-level `candidate` callable, or
      * a path to a folder containing `candidate.py`.

    Returns the loaded `candidate` object, which must conform to the
    Candidate Protocol (callable, returns CandidateOutput-like).

    The module is loaded under a unique synthetic name so repeated
    calls don't collide in `sys.modules`.
    """
    p = Path(path).resolve()
    if p.is_dir():
        p = p / "candidate.py"
    if not p.is_file() or p.suffix != ".py":
        raise FileNotFoundError(f"candidate file not found: {p}")

    mod_name = f"_loaded_candidate_{abs(hash(str(p)))}"
    spec = importlib.util.spec_from_file_location(mod_name, p)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load candidate from {p}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)

    if not hasattr(mod, "candidate"):
        raise AttributeError(
            f"{p} does not expose a module-level `candidate` attribute"
        )
    cand = mod.candidate
    if not callable(cand):
        raise TypeError(f"{p}.candidate is not callable (got {type(cand).__name__})")
    return cand


__all__ = [
    "Candidate",
    "CandidateInput",
    "CandidateOutput",
    "load_candidate",
]