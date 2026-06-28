"""Parse the zenodo text-format LLM response into a PlantUML block.

The `AutomatedDomainModelling_zenodo (the reconstruction in the local sibling repo) — see Candidates/AutomatedDomainModelling_zenodo/README.md` suite asks the LLM to
emit a structured text response of the form:

    Enumeration:
    EnumName(literal1, literal2, ...)

    Class:
    ClassName(type1 attrName1, type2 attrName2)
    abstract ClassName(...)

    Relationships:
    mul1 class1 associate mul2 class2
    mul1 class1 contain  mul2 class2
    class1 inherit class2
    class1 isA     class2        # CoT annotated H2S uses both verbs

We parse this text and synthesise a single `@startuml…@enduml` block in
the grammar that `Data.Parser` understands:

  * Cardinalities are quoted (`"1"`, `"*"`, `"0..*"`, `"1..*"`, `"0..1"`,
    `"n..m"`).
  * Inheritance is emitted as `Child --|> Parent`.
  * Composition (`contain`) is `Whole *-- Part`.
  * Association (`associate`) is `Source -- Target`.
  * Classes appear before relationships.

This module is **source-group-shared**: it lives under
`Candidates/AutomatedDomainModelling_zenodo/` and is imported by every
zenodo strategy. Strategies in other groups do NOT use it.

Tolerance:
  * Both `Enumeration` and `Enumerations` headings are accepted
    (case-insensitive).
  * Both `Class` and `Classes` headings are accepted.
  * Both `Relationship` and `Relationships` headings are accepted.
  * Leading prose before the first heading is tolerated (LLMs often
    preface their answer with a sentence).
  * Markdown fences (``` … ```) are stripped.
  * Cardinalities are emitted quoted (parser also accepts unquoted,
    but quoted matches the kaiser step-5 convention).
"""
from __future__ import annotations

import re
from typing import Optional


_ENUM_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$")
_CLASS_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$")
_ABSTRACT_RE = re.compile(r"^abstract\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$")
_ASSOC_RE = re.compile(
    r"^\s*(?P<m1>\S+)\s+(?P<c1>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?:associate|contain)\s+"
    r"(?P<m2>\S+)\s+(?P<c2>[A-Za-z_][A-Za-z0-9_]*)\s*$"
)
_INHERIT_RE = re.compile(
    r"^\s*(?P<c1>[A-Za-z_][A-Za-z0-9_]*)\s+(?:inherit|isA)\s+(?P<c2>[A-Za-z_][A-Za-z0-9_]*)\s*$",
    re.IGNORECASE,
)

_ENUM_HEADINGS = ("enumeration", "enumerations")
_CLASS_HEADINGS = ("class", "classes")
_REL_HEADINGS = ("relationship", "relationships")

_FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text)


def _find_section(text: str, headings: tuple[str, ...]) -> Optional[int]:
    """Return the 0-based line index of the first line whose stripped,
    case-folded content matches `headings` (with or without trailing colon).

    Searches from the start of `text`. Returns None if no heading found.
    """
    target = {h.rstrip(":") for h in headings}
    for i, line in enumerate(text.splitlines()):
        s = line.strip().rstrip(":").lower()
        if s in target:
            return i
    return None


def _section_lines(
    text: str, headings: tuple[str, ...], next_headings: tuple[str, ...]
) -> list[str]:
    """Return the lines belonging to the section headed by any of `headings`.

    The section starts at the first heading line and ends at the next
    heading line whose name is in `next_headings` or `headings`, or at EOF.
    """
    start = _find_section(text, headings)
    if start is None:
        return []
    next_targets = {h.rstrip(":") for h in (*headings, *next_headings)}
    out: list[str] = []
    for line in text.splitlines()[start + 1:]:
        s = line.strip().rstrip(":").lower()
        if s in next_targets:
            break
        out.append(line)
    return out


def _parse_attrs(raw: str) -> list[tuple[str, str]]:
    """Parse `type1 name1, type2 name2, …` (zenodo attribute syntax).

    Returns list of `(type, name)` tuples. If only one token is present,
    returns `[(token, "")]` (a name-only attribute). Empty input → [].
    """
    if not raw.strip():
        return []
    out: list[tuple[str, str]] = []
    for piece in raw.split(","):
        parts = piece.strip().split()
        if len(parts) >= 2:
            out.append((parts[0], " ".join(parts[1:])))
        elif len(parts) == 1:
            out.append((parts[0], ""))
    return out


def _quote_cardinality(card: str) -> str:
    """Wrap a cardinality token in double quotes if not already quoted.

    `1` → `"1"`, `0..*` → `"0..*"`, `n..m` → `"n..m"`. Already-quoted
    tokens pass through unchanged.
    """
    c = card.strip()
    if not c:
        return '""'
    if c.startswith('"') and c.endswith('"'):
        return c
    return f'"{c}"'


def text_to_plantuml(raw: str) -> Optional[str]:
    """Convert a zenodo-format text response to a PlantUML block.

    Returns None if the input does not look like a zenodo-format response
    (i.e. contains neither a Class/Classes heading nor a Relationships
    heading).
    """
    if not raw:
        return None
    text = _strip_fences(raw).strip()
    if not (
        (_find_section(text, _CLASS_HEADINGS) is not None) and
        (_find_section(text, _REL_HEADINGS) is not None)
    ):
        return None

    enums: list[tuple[str, list[str]]] = []
    classes: list[tuple[str, list[tuple[str, str]], bool]] = []

    enum_lines = _section_lines(text, _ENUM_HEADINGS, (*_CLASS_HEADINGS, *_REL_HEADINGS))
    for line in enum_lines:
        s = line.strip()
        if not s:
            continue
        m = _ENUM_RE.match(s)
        if m:
            literals = [x.strip() for x in m.group(2).split(",") if x.strip()]
            enums.append((m.group(1), literals))

    class_lines = _section_lines(text, _CLASS_HEADINGS, _REL_HEADINGS)
    for line in class_lines:
        s = line.strip()
        if not s:
            continue
        m_abs = _ABSTRACT_RE.match(s)
        m_cls = _CLASS_RE.match(s)
        if m_abs:
            attrs = _parse_attrs(m_abs.group(2))
            classes.append((m_abs.group(1), attrs, True))
        elif m_cls:
            attrs = _parse_attrs(m_cls.group(2))
            classes.append((m_cls.group(1), attrs, False))

    rel_lines = _section_lines(text, _REL_HEADINGS, ())
    lines: list[str] = ["@startuml", ""]

    for name, literals in enums:
        lines.append(f"enum {name} {{")
        for lit in literals:
            lines.append(f"  {lit}")
        lines.append("}")
        lines.append("")

    for name, attrs, is_abs in classes:
        prefix = "abstract class " if is_abs else "class "
        if not attrs:
            lines.append(f"{prefix}{name} {{ }}")
        else:
            lines.append(f"{prefix}{name} {{")
            for t, a in attrs:
                if a:
                    lines.append(f"  {t} {a}")
                else:
                    lines.append(f"  {a}")
            lines.append("}")
        lines.append("")

    for line in rel_lines:
        s = line.strip()
        if not s:
            continue
        m = _ASSOC_RE.match(s)
        if m:
            m1 = _quote_cardinality(m.group("m1"))
            m2 = _quote_cardinality(m.group("m2"))
            arrow = "*--" if "contain" in s else "--"
            lines.append(f'{m.group("c1")} {m1} {arrow} {m2} {m.group("c2")}')
            continue
        m = _INHERIT_RE.match(s)
        if m:
            lines.append(f'{m.group("c1")} --|> {m.group("c2")}')

    lines.append("@enduml")
    return "\n".join(lines)


__all__ = ["text_to_plantuml"]