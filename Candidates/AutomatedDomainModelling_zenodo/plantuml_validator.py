"""Line-by-line PlantUML validator for the zenodo strategies.

A pure-Python pre-check that runs on a PlantUML string BEFORE the
metrik-4 parser sees it. Mirrors the regex constants of
``domainModel-Metrics-Comparison/Metric-Implementation/Metrik-4/Parser/parser.py``
so anything this module accepts is also accepted by the parser, and
anything it cannot accept is flagged with a precise, line-numbered
error.

Behaviour:

  * Mechanical repairs are applied silently:
      - Missing class declarations for classes referenced in a
        relationship are added as ``class X { }``.
      - Relationship lines with endpoints that fail the identifier
        regex or are in the blocklist are dropped (the relationship
        is discarded, the classes survive).
      - Markdown code fences (```) are stripped.

  * Non-mechanical issues fail the record:
      - Missing @startuml / @enduml markers.
      - Unrecognised line kinds (not class/abstract class/enum/relationship).
      - Class names that cannot be repaired to a valid identifier.
      - Diagrams that are empty after mechanical repair.

Cardinalities are optional (mirroring the metrik-4 parser at
``parser.py:478-483``). When the validator emits a repaired diagram
it always normalises cardinalities to quoted form (``""`` for none,
``"1"`` for one, etc.).

The validator does NOT call any LLM. It is a deterministic
syntactic pre-check; the LLM-based translation lives in the
``TwoStageZeroShotCandidate`` class in
``Candidates/AutomatedDomainModelling_zenodo/zero_shot/candidate.py``.

This module is **source-group-shared**: it lives under
``Candidates/AutomatedDomainModelling_zenodo/`` and is imported by
the ``zero_shot`` strategy. Future zenodo strategies (one_shot,
two_shot, cot) can import it too. Strategies in other groups do
NOT use it.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class LineKind(str, Enum):
    CLASS = "class"
    ABSTRACT_CLASS = "abstract_class"
    CLASS_START = "class_start"
    ENUM_INLINE = "enum_inline"
    ENUM_START = "enum_start"
    RELATIONSHIP = "relationship"
    UNRECOGNISED = "unrecognised"
    BLANK = "blank"
    MARKER = "marker"


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FENCE = re.compile(r"^\s*```", re.MULTILINE)

_CLASS_INLINE = re.compile(
    r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}\s*$"
)
_CLASS_START = re.compile(
    r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$"
)
_CLASS_BARE = re.compile(
    r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*$"
)
_ABSTRACT_INLINE = re.compile(
    r"^\s*abstract\s+class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}\s*$"
)
_ABSTRACT_START = re.compile(
    r"^\s*abstract\s+class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$"
)
_ABSTRACT_BARE = re.compile(
    r"^\s*abstract\s+class\s+([A-Za-z_][A-Za-z0-9_]*)\s*$"
)
_ENUM_INLINE = re.compile(
    r"^\s*enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*([^}]+)\s*\}\s*$"
)
_ENUM_START = re.compile(
    r"^\s*enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$"
)
_ENUM_END = re.compile(r"^\s*\}\s*$")

_ARROW_GROUP = r"(?:--\|>|<\|--|-->|<--|\*--|o--|-\|>|->|<-|\.\.|--|-)"
_REL_LINE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+"
    r'(?:"([^"]*)"\s+)?'
    rf"({_ARROW_GROUP})\s+"
    r'(?:"([^"]*)"\s+)?'
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*:\s*(.+))?\s*$",
)

_NON_CLASS_TOKENS = frozenset({
    "i.e", "e.g", "etc", "cf", "vs", "al", "viz", "approx",
    "yes", "no", "true", "false",
})


@dataclass
class ValidateResult:
    ok: bool
    repaired: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def _is_valid_identifier(name: str) -> bool:
    if not name:
        return False
    if name.lower() in _NON_CLASS_TOKENS:
        return False
    return bool(_IDENTIFIER.match(name))


def _strip_fences(text: str) -> str:
    return _FENCE.sub("", text)


def _classify_line(line: str) -> LineKind:
    s = line.strip()
    if not s:
        return LineKind.BLANK
    if s.startswith("@startuml") or s.startswith("@enduml"):
        return LineKind.MARKER
    if _ABSTRACT_INLINE.match(s) or _ABSTRACT_START.match(s) or _ABSTRACT_BARE.match(s):
        return LineKind.ABSTRACT_CLASS
    if _CLASS_INLINE.match(s) or _CLASS_START.match(s) or _CLASS_BARE.match(s):
        return LineKind.CLASS
    if _ENUM_INLINE.match(s):
        return LineKind.ENUM_INLINE
    if _ENUM_START.match(s):
        return LineKind.ENUM_START
    if _REL_LINE.match(s):
        return LineKind.RELATIONSHIP
    return LineKind.UNRECOGNISED


def _extract_endpoints(line: str) -> Optional[tuple[str, str]]:
    """Return (left, right) class names from a relationship line, or None."""
    m = _REL_LINE.match(line)
    if not m:
        return None
    return m.group(1), m.group(5)


def _extract_class_name(line: str) -> Optional[str]:
    s = line.strip()
    for rx in (_ABSTRACT_INLINE, _ABSTRACT_START, _ABSTRACT_BARE,
               _CLASS_INLINE, _CLASS_START, _CLASS_BARE):
        m = rx.match(s)
        if m:
            return m.group(1)
    return None


def validate(puml: str) -> ValidateResult:
    """Validate (and mechanically repair) a PlantUML string.

    Returns a ``ValidateResult`` with the following semantics:

      * ``ok=True``  - the diagram is provably parseable; ``repaired``
                       holds the cleaned PUML (which may be the same
                       as the input if no repairs were needed).
      * ``ok=False`` - the diagram is not parseable; ``repaired`` is
                       the best-effort auto-repaired diagram (may be
                       ``None`` if repair is impossible), and
                       ``errors`` is a non-empty list of human-readable
                       failure descriptions.
    """
    if not puml or not puml.strip():
        return ValidateResult(ok=False, repaired=None, errors=["empty input"])

    text = _strip_fences(puml).strip()
    if "@startuml" not in text.lower():
        return ValidateResult(ok=False, repaired=None, errors=["missing @startuml marker"])
    if "@enduml" not in text.lower():
        return ValidateResult(ok=False, repaired=None, errors=["missing @enduml marker"])

    s_match = re.search(r"@startuml", text, re.IGNORECASE)
    e_match = re.search(r"@enduml", text, re.IGNORECASE)
    head = text[: s_match.end()]
    body = text[s_match.end(): e_match.start()]
    tail = text[e_match.start():]

    declared: set[str] = set()
    referenced: set[str] = set()
    enums: list[tuple[str, list[str]]] = []
    classes: list[tuple[str, bool, list[str]]] = []
    rels: list[tuple[str, Optional[str], str, Optional[str], str, Optional[str]]] = []

    fatal_errors: list[str] = []
    enum_name: Optional[str] = None
    enum_lits: list[str] = []
    lines = body.splitlines()

    i = 0
    while i < len(lines):
        lineno = i + 1
        raw = lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue
        if s.startswith("@startuml") or s.startswith("@enduml"):
            i += 1
            continue

        m_enum_inline = _ENUM_INLINE.match(s)
        if m_enum_inline:
            name = m_enum_inline.group(1)
            if not _is_valid_identifier(name):
                fatal_errors.append(
                    f"line {lineno}: enum name {name!r} is not a valid identifier"
                )
            else:
                lits = [x.strip() for x in m_enum_inline.group(2).split(",") if x.strip()]
                enums.append((name, lits))
            i += 1
            continue

        if enum_name is not None:
            if _ENUM_END.match(s):
                enums.append((enum_name, enum_lits))
                enum_name = None
                enum_lits = []
            else:
                lit = s
                if not _is_valid_identifier(lit):
                    fatal_errors.append(
                        f"line {lineno}: enum literal {lit!r} is not a valid identifier"
                    )
                else:
                    enum_lits.append(lit)
            i += 1
            continue

        m_enum_start = _ENUM_START.match(s)
        if m_enum_start:
            name = m_enum_start.group(1)
            if not _is_valid_identifier(name):
                fatal_errors.append(
                    f"line {lineno}: enum name {name!r} is not a valid identifier"
                )
                enum_name = None
            else:
                enum_name = name
                enum_lits = []
            i += 1
            continue

        m_abs_inline = _ABSTRACT_INLINE.match(s)
        m_abs_start = _ABSTRACT_START.match(s)
        m_abs_bare = _ABSTRACT_BARE.match(s)
        m_cls_inline = _CLASS_INLINE.match(s)
        m_cls_start = _CLASS_START.match(s)
        m_cls_bare = _CLASS_BARE.match(s)
        if (m_abs_inline or m_abs_start or m_abs_bare
                or m_cls_inline or m_cls_start or m_cls_bare):
            is_abs = bool(m_abs_inline or m_abs_start or m_abs_bare)
            if m_abs_inline:
                name = m_abs_inline.group(1)
                inner = m_abs_inline.group(2) or ""
            elif m_abs_start:
                name = m_abs_start.group(1); inner = None
            elif m_abs_bare:
                name = m_abs_bare.group(1); inner = ""
            elif m_cls_inline:
                name = m_cls_inline.group(1)
                inner = m_cls_inline.group(2) or ""
            elif m_cls_start:
                name = m_cls_start.group(1); inner = None
            else:
                name = m_cls_bare.group(1); inner = ""
            if not _is_valid_identifier(name):
                fatal_errors.append(
                    f"line {lineno}: class name {name!r} is not a valid identifier"
                )
                i += 1
                continue
            declared.add(name)
            i += 1
            if inner is None:
                attrs: list[str] = []
                while i < len(lines):
                    inner_raw = lines[i]
                    inner_line = inner_raw.strip()
                    i += 1
                    if inner_line == "}":
                        break
                    if inner_line:
                        attrs.append(inner_line)
                else:
                    fatal_errors.append(
                        f"line {lineno}: class {name!r} opened but never closed"
                    )
                classes.append((name, is_abs, attrs))
            else:
                attrs = [a.strip() for a in inner.split(";") if a.strip()] if inner else []
                classes.append((name, is_abs, attrs))
            continue

        m_rel = _REL_LINE.match(s)
        if m_rel:
            src, c1, arrow, c2, tgt, label = (
                m_rel.group(1), m_rel.group(2), m_rel.group(3),
                m_rel.group(4), m_rel.group(5), m_rel.group(6),
            )
            if not _is_valid_identifier(src):
                fatal_errors.append(
                    f"line {lineno}: relationship source {src!r} is not a valid identifier"
                )
                i += 1
                continue
            if not _is_valid_identifier(tgt):
                fatal_errors.append(
                    f"line {lineno}: relationship target {tgt!r} is not a valid identifier"
                )
                i += 1
                continue
            referenced.add(src)
            referenced.add(tgt)
            rels.append((src, c1, arrow, c2, tgt, label))
            i += 1
            continue

        fatal_errors.append(f"line {lineno}: unrecognised line {s!r}")
        i += 1

    if enum_name is not None:
        fatal_errors.append(
            f"enum {enum_name!r} opened but never closed"
        )

    if not classes and not enums and not rels:
        return ValidateResult(
            ok=False,
            repaired=None,
            errors=fatal_errors + ["empty diagram: no class, enum, or relationship lines survived"],
        )

    if fatal_errors:
        missing = sorted(referenced - declared)
        repaired_puml = _emit(head, tail, enums, classes, rels, missing)
        return ValidateResult(ok=False, repaired=repaired_puml, errors=fatal_errors)

    missing = sorted(referenced - declared)
    repaired_puml = _emit(head, tail, enums, classes, rels, missing)
    return ValidateResult(ok=True, repaired=repaired_puml, errors=[])


def _emit(
    head: str,
    tail: str,
    enums: list[tuple[str, list[str]]],
    classes: list[tuple[str, bool, list[str]]],
    rels: list[tuple[str, Optional[str], str, Optional[str], str, Optional[str]]],
    missing: list[str],
) -> str:
    parts: list[str] = [head, ""]
    for name, lits in enums:
        parts.append(f"enum {name} {{")
        for lit in lits:
            parts.append(f"  {lit}")
        parts.append("}")
        parts.append("")
    for name in missing:
        parts.append(f"class {name} {{ }}")
    for name, is_abs, attrs in classes:
        prefix = "abstract class " if is_abs else "class "
        if not attrs:
            parts.append(f"{prefix}{name} {{ }}")
        else:
            parts.append(f"{prefix}{name} {{")
            for a in attrs:
                parts.append(f"  {a}")
            parts.append("}")
        parts.append("")
    for src, c1, arrow, c2, tgt, label in rels:
        c1_str = '""' if c1 is None else f'"{c1}"'
        c2_str = '""' if c2 is None else f'"{c2}"'
        if label:
            parts.append(f'{src} {c1_str} {arrow} {c2_str} {tgt} : {label}')
        else:
            parts.append(f'{src} {c1_str} {arrow} {c2_str} {tgt}')
    parts.append("")
    parts.append(tail)
    return "\n".join(parts).rstrip() + "\n"


__all__ = [
    "LineKind",
    "ValidateResult",
    "validate",
    "_classify_line",
    "_extract_endpoints",
    "_extract_class_name",
    "_is_valid_identifier",
    "_NON_CLASS_TOKENS",
]
