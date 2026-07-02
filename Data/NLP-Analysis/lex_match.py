"""Lexical match: per-element, 4 levels (L1..L4) + absent.

L1 direct  : any token of the element appears (case-insensitive) in the NLT
L2 lemma   : any token's lemma OR its singular/plural inflection appears
             in the NLT lemma set
L3 camel   : camelCase-split token of the element appears in the NLT
L4 synonym : any token has a WordNet synset whose lemmas appear in the NLT
absent     : none of the above

We also report the sentence indices where the element (or any of its tokens)
appears, so the dep-graph stage can re-use them.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

import inflect
import nltk
from nltk.corpus import wordnet

from nlp_features import split_identifier

_ENGINE = inflect.engine()


def _plural(s: str) -> str:
    try:
        return _ENGINE.plural(s)
    except Exception:
        return s


def _singular(s: str) -> str:
    try:
        return _ENGINE.singular_noun(s) or s
    except Exception:
        return s


# ---------------------------------------------------------------------------
# NLT index
# ---------------------------------------------------------------------------

def build_nlt_index(text: str) -> Dict[str, Any]:
    """Pre-compute lookup sets for the four matching levels."""
    # Token set (lowercased words)
    raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9]*", text)
    nlt_tokens_lower: Set[str] = {t.lower() for t in raw_tokens}

    # Lemma set
    try:
        from nlp_features import get_nlp
        doc = get_nlp()(text)
        nlt_lemmas: Set[str] = {t.lemma_.lower() for t in doc
                                 if t.is_alpha and t.lemma_}
    except Exception:
        nlt_lemmas = set(nlt_tokens_lower)

    # Singular/plural forms of every NLT token
    nlt_singular: Set[str] = set()
    nlt_plural: Set[str] = set()
    for t in nlt_tokens_lower:
        nlt_singular.add(t)
        nlt_plural.add(t)
        nlt_singular.add(_singular(t))
        nlt_plural.add(_plural(t))

    # WordNet synset lemmas (light, only for words that exist in WordNet)
    nlt_wordnet_lemmas: Set[str] = set()
    for w in nlt_tokens_lower:
        for syn in wordnet.synsets(w):
            for lm in syn.lemma_names():
                nlt_wordnet_lemmas.add(lm.replace("_", " ").lower())

    # Per-sentence token index (for sentence lookup of element occurrences)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sent_token_index: List[Set[str]] = []
    for s in sentences:
        sent_token_index.append(
            {t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9]*", s)}
        )

    return {
        "tokens_lower": nlt_tokens_lower,
        "lemmas": nlt_lemmas,
        "singular": nlt_singular,
        "plural": nlt_plural,
        "wordnet_lemmas": nlt_wordnet_lemmas,
        "sentences": sentences,
        "sent_tokens": sent_token_index,
    }


# ---------------------------------------------------------------------------
# Element matching
# ---------------------------------------------------------------------------

def _sent_indices_for_tokens(name: str,
                             sent_tokens: List[Set[str]]) -> List[int]:
    toks = split_identifier(name)
    if not toks:
        return []
    hits = []
    for i, st in enumerate(sent_tokens):
        if any(t in st for t in toks):
            hits.append(i)
    return hits


def _level_hits(name: str, idx: Dict[str, Any]) -> Dict[str, bool]:
    """Compute L1..L4 + absent for a single identifier string."""
    tokens = split_identifier(name)
    if not tokens:
        # Identifier is empty/non-alphabetic; treat as absent
        return {
            "L1_direct": False, "L2_lemma": False,
            "L3_camelcase": False, "L4_synonym": False,
            "absent": True,
            "matched_tokens": "",
        }
    toks = [t.lower() for t in tokens]
    tokens_lower = idx["tokens_lower"]
    lemmas = idx["lemmas"]
    singular = idx["singular"]
    plural = idx["plural"]
    wordnet_lemmas = idx["wordnet_lemmas"]

    l1 = any(t in tokens_lower for t in toks)
    l2 = (any(t in lemmas for t in toks) or
          any(t in singular for t in toks) or
          any(t in plural for t in toks))
    l3 = l1 or any(t in tokens_lower for t in toks)  # identical to L1 by construction
    # L4: check if a WordNet synonym of any token appears in the NLT
    l4_hits = set()
    for t in toks:
        for syn in wordnet.synsets(t):
            for lm in syn.lemma_names():
                lm_clean = lm.replace("_", " ").lower()
                if lm_clean in tokens_lower or lm_clean in lemmas:
                    l4_hits.add(t)
    l4 = bool(l4_hits)
    absent = not (l1 or l2 or l3 or l4)
    return {
        "L1_direct": l1,
        "L2_lemma": l2,
        "L3_camelcase": l3,
        "L4_synonym": l4,
        "absent": absent,
        "matched_tokens": ",".join(sorted(l4_hits)),
    }


def match_class(name: str, idx: Dict[str, Any]) -> Dict[str, Any]:
    """Match a class name (e.g. 'GameArea', 'Airplane')."""
    res = _level_hits(name, idx)
    res["sent_indices"] = _sent_indices_for_tokens(name, idx["sent_tokens"])
    return res


def match_attribute(name: str, idx: Dict[str, Any]) -> Dict[str, Any]:
    res = _level_hits(name, idx)
    res["sent_indices"] = _sent_indices_for_tokens(name, idx["sent_tokens"])
    return res


def match_relationship(rel: Dict[str, Any],
                       idx: Dict[str, Any]) -> Dict[str, Any]:
    """Match both endpoints and the (optional) label of a relationship."""
    src = _level_hits(rel["source"], idx)
    tgt = _level_hits(rel["target"], idx)
    label = None
    if rel.get("label"):
        label = _level_hits(rel["label"], idx)

    # Recoverable: both endpoints have a sentence co-occurrence
    src_sents = set(_sent_indices_for_tokens(rel["source"], idx["sent_tokens"]))
    tgt_sents = set(_sent_indices_for_tokens(rel["target"], idx["sent_tokens"]))
    common_sents = sorted(src_sents & tgt_sents)

    return {
        "source_L1": src["L1_direct"], "source_L2": src["L2_lemma"],
        "source_L3": src["L3_camelcase"], "source_L4": src["L4_synonym"],
        "source_absent": src["absent"],
        "target_L1": tgt["L1_direct"], "target_L2": tgt["L2_lemma"],
        "target_L3": tgt["L3_camelcase"], "target_L4": tgt["L4_synonym"],
        "target_absent": tgt["absent"],
        "label": label,
        "common_sentences": common_sents,
        "source_sent_indices": sorted(src_sents),
        "target_sent_indices": sorted(tgt_sents),
    }


# ---------------------------------------------------------------------------
# Bulk driver
# ---------------------------------------------------------------------------

def match_all(diagram: Dict[str, Any],
              idx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply match_class/match_attribute/match_relationship to every element
    of a parsed diagram.
    """
    out = {
        "classes": [],       # [{name, ...match fields...}, ...]
        "attributes": [],    # [{class, name, ...match fields...}, ...]
        "relationships": [], # [{source, target, type, label, ...match fields...}, ...]
        "enum_values": [],   # [{enum, value, ...match fields...}, ...]
    }
    for c in diagram["classes"]:
        out["classes"].append({
            "name": c["name"],
            "is_abstract": c["is_abstract"],
            **match_class(c["name"], idx),
        })
        for a in c["attributes"]:
            out["attributes"].append({
                "class": c["name"],
                "name": a["name"],
                "type": a["type"],
                **match_attribute(a["name"], idx),
            })
    for e in diagram["enums"]:
        for v in e["values"]:
            out["enum_values"].append({
                "enum": e["name"],
                "value": v,
                **match_attribute(v, idx),
            })
    for r in diagram["relationships"]:
        out["relationships"].append({
            "source": r["source"],
            "target": r["target"],
            "type": r["type"],
            "label": r["label"],
            "src_card": r["source_card"],
            "tgt_card": r["target_card"],
            **match_relationship(r, idx),
        })
    return out


def coverage_summary(matches: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate %absent / %L1 / %L2 / %L3 / %L4 for each element kind."""
    def _agg(rows, key):
        if not rows:
            return {"n": 0, "pct_L1": 0.0, "pct_L2": 0.0,
                    "pct_L3": 0.0, "pct_L4": 0.0, "pct_absent": 0.0}
        n = len(rows)
        return {
            "n": n,
            "pct_L1": round(100 * sum(1 for r in rows if r.get("L1_direct", r.get("source_L1", False))) / n, 2),
            "pct_L2": round(100 * sum(1 for r in rows if r.get("L2_lemma", r.get("source_L2", False))) / n, 2),
            "pct_L3": round(100 * sum(1 for r in rows if r.get("L3_camelcase", r.get("source_L3", False))) / n, 2),
            "pct_L4": round(100 * sum(1 for r in rows if r.get("L4_synonym", r.get("source_L4", False))) / n, 2),
            "pct_absent": round(100 * sum(1 for r in rows if r.get("absent", r.get("source_absent", False))) / n, 2),
        }
    return {
        "classes": _agg(matches["classes"], "name"),
        "attributes": _agg(matches["attributes"], "name"),
        "enum_values": _agg(matches["enum_values"], "value"),
        "relationships_source": _agg(matches["relationships"], "source"),
        "relationships_target": _agg(matches["relationships"], "target"),
    }
