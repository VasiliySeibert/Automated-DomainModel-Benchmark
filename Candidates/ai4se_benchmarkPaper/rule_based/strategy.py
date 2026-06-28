"""Rule-based candidate — re-implementation of Abdelnabi et al. (2020).

SpaCy SVO + verb-lemma heuristic. **No LLM** — acts as a non-LLM
baseline for the benchmark.

Self-authored by Vasiliy Seibert, 2024 (originally in
`ai4se_benchmarkPaper/benchmark/candidates/rule_based/utils.py`).
This is a re-implementation of the algorithm described in:

    Abdelnabi, E. A., Maatuk, A. M., Abdelaziz, T. M., & Elakeili, S. M.
    (2020). Generating UML Class Diagram using NLP Techniques and
    Heuristic Rules. In 2020 20th Int. Conf. on Sciences and Techniques
    of Automatic Control and Computer Engineering (STA), pp. 277–282.
    IEEE. DOI: 10.1109/STA50679.2020.9329301.

The post-processing step adds explicit `class X { }` declarations so
the parser does a strict parse.

Adapted to the registry's strategy interface:
* `run(spec, nlt) -> dict` returns the standard {generated_model, failed, error, raw_excerpt}.
* `SPEC` is registered with `uses_llm=False` (no LLM).
* `model_key` is ignored — this strategy has no model.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Optional

from Candidates.registry import CandidateSpec, register

log = logging.getLogger(__name__)

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

try:
    from heuristic import generate_uml_from_text as _heuristic_generate
except Exception:  # pragma: no cover
    _heuristic_generate = None


_CLASS_LINE = re.compile(
    r"^\s*(?:abstract\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{",
    re.MULTILINE,
)
_REL_LINE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"\"[^\"]*\"\s+"
    r"(--|\*--|o--|<\\?--|-->)\s+"
    r"\"[^\"]*\"\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


def _normalise(puml: str) -> str:
    """Add explicit `class X { }` declarations for every class name
    appearing in a relationship.
    """
    if not puml:
        return puml
    start_match = re.search(r"@startuml", puml, re.IGNORECASE)
    end_match = re.search(r"@enduml", puml, re.IGNORECASE)
    if not (start_match and end_match):
        return puml
    head = puml[: start_match.end()]
    body = puml[start_match.end() : end_match.start()]
    tail = puml[end_match.start() :]

    declared = set(_CLASS_LINE.findall(body))
    referenced: set[str] = set()
    for m in _REL_LINE.finditer(body):
        referenced.add(m.group(1))
        referenced.add(m.group(3))
    missing = sorted(referenced - declared)
    if missing:
        additions = "\n".join(f"class {name} {{ }}" for name in missing) + "\n\n"
        body = additions + body

    return head + "\n\n" + body.strip("\n") + "\n\n" + tail


def run(spec: CandidateSpec, nlt: str) -> dict:
    """`spec.model` is ignored — this strategy has no LLM."""
    if _heuristic_generate is None:
        return {
            "generated_model": "", "failed": True,
            "error": "rule_based_requires_spacy: pip install spacy && "
                     "python -m spacy download en_core_web_sm",
            "raw_excerpt": "",
        }
    try:
        raw = _heuristic_generate(nlt)
        norm = _normalise(raw)
        return {
            "generated_model": norm, "failed": False,
            "error": None, "raw_excerpt": raw[:2000],
        }
    except Exception as exc:
        log.error("rule_based failed: %s", exc, exc_info=True)
        return {
            "generated_model": "", "failed": True,
            "error": f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt": "",
        }


SPEC = CandidateSpec(
    source="ai4se_benchmarkPaper",
    strategy="rule_based",
    uses_llm=False,
    skip_folders=(),
    timeout=0,
    description="spaCy SVO + verb-lemma heuristic. No LLM.",
)


register(SPEC)
__all__ = ["SPEC", "run"]