"""Dependency-graph binding between diagram elements and the NLT.

For every diagram element (class, attribute, relationship), we report:

- a "class_attr_bindings" entry whenever the attribute token sits in the
  same sentence as the class token and the dep path between them is at most
  `max_hop` edges. The shortest path through the dep tree is recorded.

- a "class_rel_bindings" entry for every pair of co-occurring class
  endpoints in a sentence, with the connecting path (typically a verb or
  preposition).

This is the "full per-record dep graph" the plan calls for: every
candidate binding is preserved, not just a hit/miss flag.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from nlp_features import get_nlp, split_identifier


# ---------------------------------------------------------------------------
# Helpers: locate tokens in the doc that correspond to a name
# ---------------------------------------------------------------------------

def _candidate_token_indices(name: str, doc) -> List[int]:
    """Indices of doc tokens whose lemma is one of the identifier's tokens.

    We consider both the original tokens and the lemmatised form so that
    'passengers' will still match 'passenger'.
    """
    parts = split_identifier(name)
    if not parts:
        return []
    parts_set = {p.lower() for p in parts}
    out = []
    for tok in doc:
        if not tok.is_alpha:
            continue
        if tok.text.lower() in parts_set or tok.lemma_.lower() in parts_set:
            out.append(tok.i)
    return out


def _shortest_dep_path(src_i: int, tgt_i: int,
                       heads: List[int]) -> Optional[List[int]]:
    """BFS upward through the head graph to find the shortest path from
    src to tgt. Returns the list of node indices including both endpoints
    or None if no path within depth limit is found.

    The dep graph is a tree rooted at the ROOT (head_i == i), so BFS through
    the head links always terminates.
    """
    if src_i == tgt_i:
        return [src_i]
    n = len(heads)
    # Build undirected adjacency (parent-child) for path search.
    adj = [[] for _ in range(n)]
    for i, h in enumerate(heads):
        if i == h:
            continue
        adj[i].append(h)
        adj[h].append(i)

    q = deque([(src_i, [src_i])])
    seen = {src_i}
    while q:
        node, path = q.popleft()
        if node == tgt_i:
            return path
        for nxt in adj[node]:
            if nxt in seen:
                continue
            seen.add(nxt)
            q.append((nxt, path + [nxt]))
    return None


def _path_text(path: Optional[List[int]], doc) -> str:
    if not path:
        return ""
    return " ".join(doc[i].text for i in path)


# ---------------------------------------------------------------------------
# Bindings
# ---------------------------------------------------------------------------

def find_class_attr_bindings(classes: List[Dict[str, Any]],
                             attributes: List[Dict[str, Any]],
                             text: str,
                             max_hop: int = 4) -> List[Dict[str, Any]]:
    """For every (class, attribute) where the class name has token hits in
    the NLT and the attribute name has token hits in the NLT, find the
    shortest dep-graph path between *any* class-token and *any*
    attribute-token in the same sentence.
    """
    nlp = get_nlp()
    doc = nlp(text)
    heads = [t.head.i for t in doc]

    # Index of token positions by lemma for fast lookup
    lemma_to_indices: Dict[str, List[int]] = {}
    for tok in doc:
        lemma_to_indices.setdefault(tok.lemma_.lower(), []).append(tok.i)
        lemma_to_indices.setdefault(tok.text.lower(), []).append(tok.i)

    bindings = []
    for c in classes:
        cname = c["name"]
        c_tokens = split_identifier(cname)
        c_token_set = {t.lower() for t in c_tokens}
        for a in attributes:
            aname = a["name"]
            a_tokens = split_identifier(aname)
            a_token_set = {t.lower() for t in a_tokens}
            if not c_token_set or not a_token_set:
                continue
            # Find candidate token pairs in the same sentence
            best = None  # (hop_count, path, sent_i, src_i, tgt_i)
            for ci, c_tok in enumerate(doc):
                if c_tok.lemma_.lower() not in c_token_set and c_tok.text.lower() not in c_token_set:
                    continue
                for ai, a_tok in enumerate(doc):
                    if a_tok.lemma_.lower() not in a_token_set and a_tok.text.lower() not in a_token_set:
                        continue
                    if c_tok.sent != a_tok.sent:
                        continue
                    path = _shortest_dep_path(c_tok.i, a_tok.i, heads)
                    if not path:
                        continue
                    hop = len(path) - 1
                    if hop > max_hop:
                        continue
                    if best is None or hop < best[0]:
                        best = (hop, path, c_tok.sent.start, c_tok.i, a_tok.i,
                                c_tok.text, a_tok.text)
            if best:
                hop, path, sent_i, src_i, tgt_i, src_text, tgt_text = best
                bindings.append({
                    "class": cname,
                    "attribute": aname,
                    "class_token": src_text,
                    "attr_token": tgt_text,
                    "sent_i": sent_i,
                    "path": path,
                    "path_text": _path_text(path, doc),
                    "hop_count": hop,
                })
    return bindings


def find_relationship_bindings(relationships: List[Dict[str, Any]],
                               text: str,
                               max_hop: int = 5) -> List[Dict[str, Any]]:
    """For every relationship (A -kind-> B), for every sentence containing
    tokens of A and tokens of B, find the shortest dep path between the
    nearest pair.
    """
    nlp = get_nlp()
    doc = nlp(text)
    heads = [t.head.i for t in doc]

    out = []
    for r in relationships:
        a_name = r["source"]
        b_name = r["target"]
        a_tokens = {t.lower() for t in split_identifier(a_name)}
        b_tokens = {t.lower() for t in split_identifier(b_name)}
        if not a_tokens or not b_tokens:
            continue
        a_idxs = [i for i, t in enumerate(doc)
                  if (t.lemma_.lower() in a_tokens or t.text.lower() in a_tokens)]
        b_idxs = [i for i, t in enumerate(doc)
                  if (t.lemma_.lower() in b_tokens or t.text.lower() in b_tokens)]
        if not a_idxs or not b_idxs:
            continue
        # Group by sentence
        from collections import defaultdict
        by_sent: Dict[Any, List[int]] = defaultdict(list)
        for i in a_idxs + b_idxs:
            by_sent[doc[i].sent].append(i)
        per_sentence_paths = []
        for sent, idxs in by_sent.items():
            a_in_sent = [i for i in idxs if i in set(a_idxs)]
            b_in_sent = [i for i in idxs if i in set(b_idxs)]
            if not a_in_sent or not b_in_sent:
                continue
            best = None
            for ai in a_in_sent:
                for bi in b_in_sent:
                    p = _shortest_dep_path(ai, bi, heads)
                    if not p:
                        continue
                    hop = len(p) - 1
                    if hop > max_hop:
                        continue
                    if best is None or hop < best[0]:
                        best = (hop, p, ai, bi)
            if best:
                hop, p, ai, bi = best
                per_sentence_paths.append({
                    "sent_i": sent.start,
                    "sent_text": sent.text,
                    "path": p,
                    "path_text": _path_text(p, doc),
                    "hop_count": hop,
                    "src_token": doc[ai].text,
                    "tgt_token": doc[bi].text,
                })
        if per_sentence_paths:
            best_overall = min(per_sentence_paths, key=lambda x: x["hop_count"])
            out.append({
                "source": a_name,
                "target": b_name,
                "type": r["type"],
                "label": r["label"],
                "n_sentences_with_both": len(per_sentence_paths),
                "best": best_overall,
                "all_sentences": per_sentence_paths,
            })
    return out


# ---------------------------------------------------------------------------
# Per-record binding summary
# ---------------------------------------------------------------------------

def binding_summary(diagram: Dict[str, Any],
                    class_attr_bindings: List[Dict[str, Any]],
                    rel_bindings: List[Dict[str, Any]]) -> Dict[str, Any]:
    n_attrs = sum(len(c["attributes"]) for c in diagram["classes"])
    n_rels = len(diagram["relationships"])
    bound_attrs = {b["attribute"] for b in class_attr_bindings}
    bound_rels = {(b["source"], b["target"]) for b in rel_bindings}
    return {
        "n_attrs_total": n_attrs,
        "n_attrs_bound": len(bound_attrs),
        "pct_attrs_bound": round(100 * len(bound_attrs) / max(1, n_attrs), 2),
        "n_rels_total": n_rels,
        "n_rels_bound": len(bound_rels),
        "pct_rels_bound": round(100 * len(bound_rels) / max(1, n_rels), 2),
        "avg_hop_class_attr": (
            round(sum(b["hop_count"] for b in class_attr_bindings) /
                  max(1, len(class_attr_bindings)), 3)
        ),
        "avg_hop_rel": (
            round(sum(b["best"]["hop_count"] for b in rel_bindings) /
                  max(1, len(rel_bindings)), 3)
        ),
    }
