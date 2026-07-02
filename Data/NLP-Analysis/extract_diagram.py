"""Thin wrapper around Data/Parser/parser.py.

Produces a normalised dict for every PUML string. We never re-parse with
regex - the project parser is the single source of truth.
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

# Make the Data package importable so we can use Data.Parser
_PARSER_PARENT = Path(__file__).resolve().parents[1]
if str(_PARSER_PARENT.parent) not in sys.path:
    sys.path.insert(0, str(_PARSER_PARENT.parent))
if str(_PARSER_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARSER_PARENT))

from Parser.parser import PlantUMLParser
from Parser.models import ParsedModel, RelationshipType


def _rel_type_str(rt: RelationshipType) -> str:
    """Normalise the relationship type to the 7 canonical PUML kinds."""
    return rt.value


def extract(puml: str) -> Dict[str, Any]:
    """Return a JSON-safe dict representation of a PlantUML string."""
    parser = PlantUMLParser(strict=False)
    model: ParsedModel = parser.parse(puml)

    classes = []
    for c in model.classes:
        classes.append({
            "name": c.name,
            "is_abstract": c.is_abstract,
            "attributes": [
                {
                    "name": a.name,
                    "type": a.type,
                    "default_value": a.default_value,
                    "is_constant": a.is_constant,
                }
                for a in c.attributes
            ],
            "nested_enum_names": [e.name for e in c.nested_enums],
        })

    enums = [
        {"name": e.name, "values": e.values, "is_inline": e.is_inline}
        for e in model.enums
    ]

    rels = []
    for r in model.relationships:
        rels.append({
            "source": r.source,
            "target": r.target,
            "type": _rel_type_str(r.relationship_type),
            "source_card": r.source_cardinality,
            "target_card": r.target_cardinality,
            "label": r.label,
            "association_members": (
                list(r.association_members) if r.association_members else None
            ),
        })

    return {
        "classes": classes,
        "enums": enums,
        "relationships": rels,
        "implicit_classes": list(model.implicit_classes),
        "notes": [{"content": n.content, "position": n.position} for n in model.notes],
        "warnings": list(parser.warnings),
    }


def all_class_names(d: Dict[str, Any]) -> List[str]:
    """All class names (explicit + implicit)."""
    explicit = [c["name"] for c in d["classes"]]
    return sorted(set(explicit + d.get("implicit_classes", [])))


def all_attribute_names(d: Dict[str, Any]) -> List[str]:
    """Attribute names with the parent class for context."""
    out = []
    for c in d["classes"]:
        for a in c["attributes"]:
            out.append({"class": c["name"], "name": a["name"], "type": a["type"]})
    return out


def all_relationship_endpoints(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Each endpoint as a separate (name, role, type, cardinality) row."""
    out = []
    for r in d["relationships"]:
        out.append({"name": r["source"], "role": "source", "type": r["type"],
                    "card": r["source_card"], "label": r["label"]})
        out.append({"name": r["target"], "role": "target", "type": r["type"],
                    "card": r["target_card"], "label": r["label"]})
        if r.get("association_members"):
            for m in r["association_members"]:
                out.append({"name": m, "role": "assoc_member", "type": r["type"],
                            "card": None, "label": r["label"]})
    return out


def summarise(d: Dict[str, Any]) -> Dict[str, int]:
    """Quick count summary used by the per-record CSV."""
    rel_types = {}
    for r in d["relationships"]:
        rel_types[r["type"]] = rel_types.get(r["type"], 0) + 1
    n_attrs = sum(len(c["attributes"]) for c in d["classes"])
    n_with_card = sum(1 for r in d["relationships"]
                      if r["source_card"] or r["target_card"])
    n_with_label = sum(1 for r in d["relationships"] if r["label"])
    return {
        "n_classes": len(d["classes"]),
        "n_enums": len(d["enums"]),
        "n_implicit_classes": len(d["implicit_classes"]),
        "n_attributes": n_attrs,
        "n_relationships": len(d["relationships"]),
        "n_rels_with_card": n_with_card,
        "n_rels_with_label": n_with_label,
        **{f"n_rels_{k}": v for k, v in rel_types.items()},
    }
