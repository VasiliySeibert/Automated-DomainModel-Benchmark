"""Parse the zenodo text format into a PlantUML block.

The `AutomatedDomainModelling-zenodo/prompts.md` suite has the LLM emit a
structured text response of the form:

    Enumeration:
    EnumName(literal1, literal2, ...)

    Class:
    ClassName(type1 attrName1, type2 attrName2)
    abstract ClassName(...)

    Relationships:
    mul1 class1 associate mul2 class2
    mul1 class1 contain mul2 class2
    class1 inherit class2

We parse this text and synthesise a single PlantUML block in the grammar
the `Data.Parser` understands (classes/enums first, then relationships,
quoted cardinalities, `--|>` for inheritance, `*--` for composition).

This module is **source-group-shared**: it lives under
`Candidates/AutomatedDomainModelling-zenodo/` and is imported by all five
zenodo strategies. Strategies in other groups do NOT use it.
"""
from __future__ import annotations

import re
from typing import Optional


_ENUM_RE     = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$")
_CLASS_RE    = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$")
_ABSTRACT_RE = re.compile(r"^abstract\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$")
_ASSOC_RE    = re.compile(
    r"^\s*(?P<m1>\S+)\s+(?P<c1>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?:associate|contain)\s+"
    r"(?P<m2>\S+)\s+(?P<c2>[A-Za-z_][A-Za-z0-9_]*)\s*$"
)
_INHERIT_RE  = re.compile(
    r"^\s*(?P<c1>[A-Za-z_][A-Za-z0-9_]*)\s+inherit\s+(?P<c2>[A-Za-z_][A-Za-z0-9_]*)\s*$"
)


def _section_block(text: str, headings: list[str]) -> str:
    out: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if not capture:
            for h in headings:
                if stripped == h or stripped == h + ":":
                    capture = True
                    break
            continue
        if stripped.endswith(":") and stripped[:-1] in {
            "Enumeration", "Enumerations",
            "Class", "Classes",
            "Relationships", "Relationship",
        }:
            break
        out.append(line)
    return "\n".join(out)


def _parse_attrs(raw: str) -> list[tuple[str, str]]:
    if not raw.strip():
        return []
    attrs: list[tuple[str, str]] = []
    for piece in raw.split(","):
        parts = piece.strip().split()
        if len(parts) >= 2:
            attrs.append((parts[0], " ".join(parts[1:])))
        elif len(parts) == 1:
            attrs.append((parts[0], ""))
    return attrs


def text_to_plantuml(raw: str) -> Optional[str]:
    """Convert a zenodo-format text response to a PlantUML block.

    Returns None if the input does not look like a zenodo-format response.
    """
    if not raw:
        return None
    text = raw.strip()
    if not (("Class" in text or "Classes" in text) and
            ("Relationship" in text or "Relationships" in text)):
        return None

    enums: list[tuple[str, list[str]]] = []
    classes: list[tuple[str, list[tuple[str, str]], bool]] = []

    enum_block  = _section_block(text, ["Enumeration", "Enumerations"])
    class_block = _section_block(text, ["Class", "Classes"])
    rel_block   = _section_block(text, ["Relationships", "Relationship"])

    for line in enum_block.splitlines():
        s = line.strip()
        if not s:
            continue
        m = _ENUM_RE.match(s)
        if m:
            literals = [x.strip() for x in m.group(2).split(",") if x.strip()]
            enums.append((m.group(1), literals))

    for line in class_block.splitlines():
        s = line.strip()
        if not s:
            continue
        m = _ABSTRACT_RE.match(s) or _CLASS_RE.match(s)
        if m:
            name = m.group(1)
            attrs = _parse_attrs(m.group(2))
            is_abs = bool(_ABSTRACT_RE.match(s))
            classes.append((name, attrs, is_abs))

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
                lines.append(f"  {t} {a}")
            lines.append("}")
        lines.append("")

    for line in rel_block.splitlines():
        s = line.strip()
        if not s:
            continue
        m = _ASSOC_RE.match(s)
        if m:
            m1, c1, m2, c2 = m.group("m1"), m.group("c1"), m.group("m2"), m.group("c2")
            arrow = "*--" if "contain" in s else "--"
            lines.append(f'{c1} "{m1}" {arrow} "{m2}" {c2}')
            continue
        m = _INHERIT_RE.match(s)
        if m:
            lines.append(f"{m.group('c1')} --|> {m.group('c2')}")

    lines.append("@enduml")
    return "\n".join(lines)


__all__ = ["text_to_plantuml"]