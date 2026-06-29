"""Dummy candidate — deterministic constant output.

Always emits the same hard-coded PlantUML block, regardless of the
input NLT. No LLM, no external dependencies, no parsing.

Purpose:
  * Smoke-test the `Workflow/Benchmark-Workflow/generate.py` →
    `Workflow/Benchmark-Workflow/score.py` →
    `Workflow/Benchmark-Workflow/visualise.py` pipeline end-to-end
    without paying LLM latency or requiring Ollama to be running.
    Drive it with `Candidates/dummy_candidate/run.py`.
  * Provide a known, reproducible output for schema inspection
    (open `Workflow/Results/dummy_candidate/<dataset>.json` and see
    exactly what shape every record has).
  * Sanity-check the metric plumbing: scoring the same PUML against
    every reference yields a deterministic per-record score pattern
    that we can diff against future runs.

Conforms to the `Candidate` Protocol from `Candidates/candidate_interface.py`
by exposing a module-level `candidate` callable.
"""
from __future__ import annotations

from Candidates.candidate_interface import CandidateOutput


_PUML = (
    "@startuml\n"
    "class Book {\n"
    "  String title\n"
    "  Integer year\n"
    "}\n"
    "class Author {\n"
    "  String name\n"
    "}\n"
    "class Library {\n"
    "  String name\n"
    "}\n"
    'Book "*" -- "1" Author : writtenBy\n'
    'Library "1" o-- "*" Book : holds\n'
    "@enduml"
)


class DummyCandidate:
    """A Candidate that always returns the same PlantUML block."""

    def __call__(self, nlt: str) -> CandidateOutput:
        return CandidateOutput(
            generated_model=_PUML,
            failed=False,
            error=None,
            raw_excerpt=_PUML[:2000],
        )


candidate = DummyCandidate()

__all__ = ["candidate", "DummyCandidate"]