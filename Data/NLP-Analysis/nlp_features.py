"""Surface-level NLT features (no model needed) and spaCy-based features.

Two groups:
- text_features(): pure tokenisation/word counts (cheap, no model)
- spacy_features(text): spaCy doc-level stats (NER, noun-chunks, dep density, passive ratio)
- dep_graph(text): the full per-token dep graph we will use later for binding
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import spacy

# Load once at import time.
_NLP = None


def get_nlp():
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm")
    return _NLP


# ---------------------------------------------------------------------------
# Cheap text features (no model)
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"\b\w+\b")
_SENT_RE = re.compile(r"[.!?]+")


def text_features(text: str) -> Dict[str, Any]:
    """Pure-Python text statistics that don't need a model."""
    words = _WORD_RE.findall(text)
    sents = [s for s in _SENT_RE.split(text) if s.strip()]
    n_words = len(words)
    n_sents = max(1, len(sents))
    n_chars = len(text)
    n_unique = len(set(w.lower() for w in words))
    ttr = n_unique / n_words if n_words else 0.0
    avg_word_len = (sum(len(w) for w in words) / n_words) if n_words else 0.0
    avg_sent_len = n_words / n_sents
    return {
        "n_chars": n_chars,
        "n_words": n_words,
        "n_sentences": len(sents),
        "n_unique_words_lower": n_unique,
        "type_token_ratio": round(ttr, 4),
        "avg_word_length": round(avg_word_len, 3),
        "avg_sentence_length_words": round(avg_sent_len, 2),
    }


# ---------------------------------------------------------------------------
# spaCy features
# ---------------------------------------------------------------------------

def spacy_features(text: str) -> Dict[str, Any]:
    """Run spaCy once and report doc-level statistics."""
    nlp = get_nlp()
    doc = nlp(text)
    n_tok = len(doc)
    n_sents = sum(1 for _ in doc.sents)
    n_nsubj = sum(1 for t in doc if t.dep_ == "nsubj")
    n_nsubjpass = sum(1 for t in doc if t.dep_ == "nsubjpass")
    n_dobj = sum(1 for t in doc if t.dep_ == "dobj")
    n_verb = sum(1 for t in doc if t.pos_ == "VERB")
    n_nouns = sum(1 for t in doc if t.pos_ in ("NOUN", "PROPN"))
    n_adj = sum(1 for t in doc if t.pos_ == "ADJ")
    n_chunks = sum(1 for _ in doc.noun_chunks)
    ents = {}
    for ent in doc.ents:
        ents[ent.label_] = ents.get(ent.label_, 0) + 1

    # average dependency out-degree: number of children per token
    if n_tok:
        avg_children = sum(len(list(t.children)) for t in doc) / n_tok
        avg_path_len = _avg_dep_path_length(doc)
    else:
        avg_children = 0.0
        avg_path_len = 0.0

    return {
        "n_tokens": n_tok,
        "n_sents_spacy": n_sents,
        "n_nsubj": n_nsubj,
        "n_nsubjpass": n_nsubjpass,
        "n_dobj": n_dobj,
        "n_verbs": n_verb,
        "n_nouns": n_nouns,
        "n_adjectives": n_adj,
        "n_noun_chunks": n_chunks,
        "n_entities": sum(ents.values()),
        "entity_types": ";".join(f"{k}:{v}" for k, v in sorted(ents.items())),
        "passive_ratio": round(n_nsubjpass / max(1, n_nsubj), 4),
        "avg_dep_children_per_token": round(avg_children, 3),
        "avg_dep_path_length": round(avg_path_len, 3),
        "n_unique_lemmas": len({t.lemma_.lower() for t in doc if t.is_alpha}),
    }


def _avg_dep_path_length(doc) -> float:
    """Mean token-to-root distance in the dependency tree."""
    if not doc:
        return 0.0
    total = 0
    n = 0
    for tok in doc:
        d = 0
        cur = tok
        while cur.head is not cur and d < 32:
            cur = cur.head
            d += 1
        total += d
        n += 1
    return total / max(1, n)


# ---------------------------------------------------------------------------
# Full dependency graph (one serialisable structure)
# ---------------------------------------------------------------------------

def dep_graph(text: str) -> Dict[str, Any]:
    """Serialise spaCy's dep parse for later use.

    The graph is represented as a list of nodes and a list of edges, so
    downstream code can search it without re-running spaCy.
    """
    nlp = get_nlp()
    doc = nlp(text)
    nodes = []
    edges = []
    sent_starts = {}

    # Build a sentence index for every token.
    for sent_i, sent in enumerate(doc.sents):
        for tok in sent:
            sent_starts[tok.i] = sent_i

    for tok in doc:
        nodes.append({
            "i": tok.i,
            "text": tok.text,
            "lemma": tok.lemma_,
            "pos": tok.pos_,
            "tag": tok.tag_,
            "dep": tok.dep_,
            "head_i": tok.head.i,
            "sent_i": sent_starts.get(tok.i, 0),
            "is_alpha": tok.is_alpha,
            "is_stop": tok.is_stop,
        })
        if tok.head is not tok:
            edges.append({
                "src": tok.head.i,
                "tgt": tok.i,
                "dep": tok.dep_,
            })

    # Noun chunks as their own list
    chunks = []
    for chunk in doc.noun_chunks:
        chunks.append({
            "text": chunk.text,
            "root_i": chunk.root.i,
            "root_text": chunk.root.text,
            "root_lemma": chunk.root.lemma_,
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "noun_chunks": chunks,
    }


# ---------------------------------------------------------------------------
# Helpers used by lex_match and dep_match
# ---------------------------------------------------------------------------

CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|[_\-]+")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def split_identifier(name: str) -> List[str]:
    """Split a camelCase / PascalCase / snake_case identifier into tokens.

    Examples:
        GameArea -> ['Game', 'Area']
        firstName -> ['first', 'Name']
        grid_horizontal_position -> ['grid', 'horizontal', 'position']
    """
    parts = CAMEL_RE.split(name)
    out: List[str] = []
    for p in parts:
        for w in WORD_RE.findall(p):
            out.append(w.lower())
    return [w for w in out if w]
