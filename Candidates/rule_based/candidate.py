"""Rule-based candidate — re-implementation of Abdelnabi et al. (2020).

Non-LLM baseline. Extracts OO concepts (classes, attributes,
relationships) from natural-language requirements using spaCy
dependency parsing and hand-tuned heuristic rules — **no LLM call**.

Re-implementation of the algorithm described in:

    Abdelnabi, E. A., Maatuk, A. M., Abdelaziz, T. M., & Elakeili, S. M.
    (2020). Generating UML Class Diagram using NLP Techniques and
    Heuristic Rules. In 2020 20th Int. Conf. on Sciences and Techniques
    of Automatic Control and Computer Engineering (STA), pp. 277–282.
    IEEE. DOI: 10.1109/STA50679.2020.9329301.

Self-authored by Vasiliy Seibert, 2024 (originally in
`ai4se_benchmarkPaper/benchmark/candidates/rule_based/utils.py`).

Conforms to the `Candidate` Protocol from `Candidates/candidate_interface.py`
by exposing a module-level `candidate` callable.

The post-processing step adds explicit `class X { }` declarations so
the parser does a strict parse.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

from Candidates.candidate_interface import CandidateOutput

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

# Strict counterpart: enforces identifier-shaped source and target,
# tolerates a trailing ` : label`. Used by the defensive sanitiser
# below to drop any relationship line whose endpoints are missing or
# sentence-adverb tokens.
_REL_LINE_STRICT = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"\"[^\"]*\"\s+"
    r"(--|\*--|o--|<\\?--|-->)\s+"
    r"\"[^\"]*\"\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)

# Inheritance form (`Parent <|-- Child`) — separate regex because the
# arrow set differs from the cardinality-carrying relationships above.
_INHERIT_LINE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s+<\|--\s+([A-Za-z_][A-Za-z0-9_]*)\s*$",
)

# Sentence adverbs / parenthetical markers that the upstream metrik
# parsers (strict mode) reject as class identifiers. Mirrors the
# blocklist inside `heuristic.py` so any future regression is also
# caught here.
_NON_CLASS_TOKENS = {
    "i.e", "e.g", "etc", "cf", "vs", "al", "viz", "approx",
    "yes", "no", "true", "false",
}

_ARROW_PATTERN = re.compile(r"--|\*--|o--|<\\?--|-->|<\|--")


def _sanitise_body(body: str) -> str:
    """Defensive: drop any relationship line that the strict parser
    would reject (missing identifier on either side; blocklisted
    sentence-adverb endpoint). Class declarations and blank lines
    pass through unchanged.
    """
    out: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("@") or s.startswith("class ") or s.startswith("abstract class "):
            out.append(line)
            continue
        if not _ARROW_PATTERN.search(s):
            out.append(line)
            continue
        m_rel = _REL_LINE_STRICT.match(s)
        if m_rel:
            src, tgt = m_rel.group(1), m_rel.group(3)
            if src.lower() not in _NON_CLASS_TOKENS and tgt.lower() not in _NON_CLASS_TOKENS:
                out.append(line)
                continue
        m_inh = _INHERIT_LINE.match(s)
        if m_inh:
            src, tgt = m_inh.group(1), m_inh.group(2)
            if src.lower() not in _NON_CLASS_TOKENS and tgt.lower() not in _NON_CLASS_TOKENS:
                out.append(line)
                continue
        log.warning("rule_based: dropping malformed line: %r", s)
    return "\n".join(out)


def _normalise(puml: str) -> str:
    """Add explicit `class X { }` declarations for every class name
    appearing in a relationship, and drop any relationship line that
    the strict metrik parser would reject.
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

    body = _sanitise_body(body)

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


class RuleBasedCandidate:
    """Non-LLM candidate: spaCy SVO + verb-lemma heuristic.

    Ignores any model parameter — this strategy has no LLM.
    """

    def __call__(self, nlt: str) -> CandidateOutput:
        if _heuristic_generate is None:
            return CandidateOutput(
                generated_model="",
                failed=True,
                error="rule_based_requires_spacy: pip install spacy && "
                      "python -m spacy download en_core_web_sm",
                raw_excerpt="",
            )
        try:
            raw = _heuristic_generate(nlt)
            norm = _normalise(raw)
            return CandidateOutput(
                generated_model=norm,
                failed=False,
                error=None,
                raw_excerpt=raw[:2000],
            )
        except Exception as exc:
            log.error("rule_based failed: %s", exc, exc_info=True)
            return CandidateOutput(
                generated_model="",
                failed=True,
                error=f"exception: {type(exc).__name__}: {exc}",
                raw_excerpt="",
            )


candidate = RuleBasedCandidate()

__all__ = ["candidate", "RuleBasedCandidate"]