"""Cross-reference between kaiser_clean and data_source_3_clean.

Both datasets share 45 ids and identical NLTs but their reference PUMLs
differ. This module quantifies where and how.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set


def _set(lst: List[str]) -> Set[str]:
    return set(lst)


def element_set(diagram: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Collect the relevant element sets from a parsed diagram.

    Class names are normalised to lower-case so the Jaccard is robust to
    trivial case differences (e.g. 'Airplane' vs 'airplane').
    """
    classes = {c["name"].lower() for c in diagram["classes"]}
    classes |= {c.lower() for c in diagram.get("implicit_classes", [])}
    attrs = {(c["name"].lower(), a["name"].lower())
             for c in diagram["classes"] for a in c["attributes"]}
    rels = set()
    for r in diagram["relationships"]:
        s = r["source"].lower()
        t = r["target"].lower()
        # Use a frozenset so the direction doesn't matter for Jaccard;
        # but also keep a direction-aware version for fine-grained diff.
        rels.add(("unordered", frozenset({s, t})))
        rels.add(("ordered", s, t, r["type"]))
    enum_values = {(e["name"].lower(), v.lower())
                   for e in diagram["enums"] for v in e["values"]}
    return {
        "classes": classes,
        "attributes": attrs,
        "relationships_unordered": {
            x[1] for x in rels if x[0] == "unordered"
        },
        "relationships_ordered_type": {
            x[1:] for x in rels if x[0] == "ordered"
        },
        "enum_values": enum_values,
    }


def jaccard(a: Set, b: Set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 4)


def diff_sets(a: Set, b: Set) -> Dict[str, List]:
    return {
        "only_in_first": sorted(a - b),
        "only_in_second": sorted(b - a),
        "intersection": sorted(a & b),
    }


def compare(diagram_a: Dict[str, Any], diagram_b: Dict[str, Any],
            label_a: str, label_b: str) -> Dict[str, Any]:
    """Compare two parsed diagrams element-by-element."""
    a = element_set(diagram_a)
    b = element_set(diagram_b)
    return {
        f"jaccard_classes_{label_a}_vs_{label_b}": jaccard(a["classes"], b["classes"]),
        f"jaccard_attributes_{label_a}_vs_{label_b}": jaccard(a["attributes"], b["attributes"]),
        f"jaccard_rels_{label_a}_vs_{label_b}": jaccard(a["relationships_unordered"], b["relationships_unordered"]),
        f"jaccard_enum_values_{label_a}_vs_{label_b}": jaccard(a["enum_values"], b["enum_values"]),
        f"diff_classes_{label_a}_vs_{label_b}": diff_sets(a["classes"], b["classes"]),
        f"diff_attributes_{label_a}_vs_{label_b}": diff_sets(a["attributes"], b["attributes"]),
        f"diff_rels_{label_a}_vs_{label_b}": diff_sets(a["relationships_unordered"], b["relationships_unordered"]),
    }
