"""Main entry point: run the full pipeline over one or more datasets."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set

import pandas as pd

# Make the package importable
_HERE = Path(__file__).resolve().parent
_DATA = _HERE.parent
_REPO = _DATA.parent
for p in (str(_REPO), str(_DATA)):
    if p not in sys.path:
        sys.path.insert(0, p)

from extract_diagram import extract, summarise
from nlp_features import text_features, spacy_features, dep_graph
import nlp_features
from lex_match import build_nlt_index, match_all, coverage_summary
from dep_match import (
    find_class_attr_bindings,
    find_relationship_bindings,
    binding_summary,
)
from cross_ref import compare, element_set

DATASETS = {
    "kaiser": _DATA / "data-source-1" / "kaiser_clean.json",
    "reference": _DATA / "data-source-2" / "reference_clean.json",
    "data_source_3": _DATA / "data-source-3" / "data_source_3_clean.json",
}


def load_dataset(name: str) -> List[Dict[str, Any]]:
    p = DATASETS[name]
    with open(p) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Extra A: per-relationship-kind coverage
# ---------------------------------------------------------------------------

REL_KINDS = ["association", "directed", "inheritance", "composition",
             "aggregation", "dependency", "association_class"]


def _rel_kind_coverage(diagram: Dict[str, Any],
                       rel_bindings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """For each of the 7 PUML relationship kinds, compute n and pct
    recoverable from a sentence in the NLT.
    """
    bound_pairs = {(b["source"], b["target"]) for b in rel_bindings}
    rows = []
    for kind in REL_KINDS:
        members = [r for r in diagram["relationships"] if r["type"] == kind]
        n = len(members)
        if n == 0:
            rows.append({"rel_kind": kind, "n": 0, "n_bound": 0, "pct_bound": 0.0})
            continue
        n_bound = sum(1 for r in members
                      if (r["source"], r["target"]) in bound_pairs)
        rows.append({
            "rel_kind": kind,
            "n": n,
            "n_bound": n_bound,
            "pct_bound": round(100 * n_bound / n, 2),
        })
    return rows


# ---------------------------------------------------------------------------
# Extra C: sentence-level statistics
# ---------------------------------------------------------------------------

def _sentence_stats(nlt: str, dg: Dict[str, Any],
                    matches: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One row per sentence. Count class/attribute/rel-endpoint hits."""
    sentences = re.split(r"(?<=[.!?])\s+", nlt.strip())
    if not sentences:
        sentences = [nlt]
    # Pre-compute the set of class/attribute/rel-endpoint names (camel-split lowercased)
    class_tokens: Set[str] = set()
    for c in matches["classes"]:
        class_tokens |= set(nlp_features.split_identifier(c["name"]))
    attr_tokens: Set[str] = set()
    for a in matches["attributes"]:
        attr_tokens |= set(nlp_features.split_identifier(a["name"]))
    rel_tokens: Set[str] = set()
    for r in matches["relationships"]:
        rel_tokens |= set(nlp_features.split_identifier(r["source"]))
        rel_tokens |= set(nlp_features.split_identifier(r["target"]))

    # Map dep-graph token indices to sentence index (already in dg["nodes"])
    sent_of = {n["i"]: n["sent_i"] for n in dg["nodes"]}

    # sentence length in words (alphanumeric tokens)
    rows = []
    for i, sent in enumerate(sentences):
        words = re.findall(r"\b\w+\b", sent)
        word_set = {w.lower() for w in words}
        rows.append({
            "sent_i": i,
            "n_words": len(words),
            "n_class_hits": len(word_set & class_tokens),
            "n_attr_hits": len(word_set & attr_tokens),
            "n_rel_endpoint_hits": len(word_set & rel_tokens),
            "n_tokens_spacy": sum(1 for n in dg["nodes"] if n["sent_i"] == i),
        })
    return rows


# ---------------------------------------------------------------------------
# Extra E: NLT style features (passive, hedge, modal, entity density)
# ---------------------------------------------------------------------------

HEDGE_WORDS = {"may", "can", "could", "might", "would", "should",
               "typically", "often", "usually", "sometimes",
               "possibly", "perhaps", "probably", "likely"}
MODAL_VERBS = {"can", "could", "may", "might", "must", "shall",
               "should", "will", "would"}


def _nlt_style_features(nlt: str, dg: Dict[str, Any]) -> Dict[str, Any]:
    """Style features from the dep graph."""
    n_tokens = max(1, len(dg["nodes"]))
    n_passive = sum(1 for n in dg["nodes"] if n["dep"] == "nsubjpass")
    n_active = sum(1 for n in dg["nodes"] if n["dep"] == "nsubj")
    n_modal = sum(1 for n in dg["nodes"]
                  if n["lemma"].lower() in MODAL_VERBS and n["pos"] in ("VERB", "AUX"))
    n_hedge = sum(1 for n in dg["nodes"]
                  if n["lemma"].lower() in HEDGE_WORDS)
    n_entities = sum(1 for n in dg["nodes"]
                     if n.get("ent_type") and n["ent_type"] != "")
    # ent_type is not in the simplified nodes we store; fall back to a quick
    # spaCy run if available
    try:
        from nlp_features import get_nlp
        doc = get_nlp()(nlt)
        n_entities = len(doc.ents)
    except Exception:
        pass
    return {
        "passive_nsubjpass": n_passive,
        "active_nsubj": n_active,
        "modal_count": n_modal,
        "hedge_count": n_hedge,
        "named_entities": n_entities,
        "passive_ratio": round(n_passive / max(1, n_passive + n_active), 4),
        "hedge_density": round(n_hedge / n_tokens, 4),
        "modal_density": round(n_modal / n_tokens, 4),
        "entity_density": round(n_entities / n_tokens, 4),
    }


# ---------------------------------------------------------------------------
# Extra M: parser warnings
# ---------------------------------------------------------------------------

def _parser_warnings(diagram: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The sidecar diagram has the warnings collected by PlantUMLParser."""
    return list(diagram.get("warnings", []))


# ---------------------------------------------------------------------------
# Per-record analysis
# ---------------------------------------------------------------------------

def analyse_record(dataset: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    """Return a flat per-record dict that goes into the wide CSV."""
    nlt = rec["nlt"]
    puml = rec["puml"]

    t0 = time.time()
    diagram = extract(puml)
    t_diagram = time.time() - t0

    t0 = time.time()
    nlt_idx = build_nlt_index(nlt)
    t_idx = time.time() - t0

    t0 = time.time()
    matches = match_all(diagram, nlt_idx)
    t_match = time.time() - t0

    t0 = time.time()
    class_attr_bindings = find_class_attr_bindings(
        diagram["classes"], diagram["classes"] and [
            {"class": c["name"], "name": a["name"]}
            for c in diagram["classes"] for a in c["attributes"]
        ] or [],
        nlt,
    )
    t_ca = time.time() - t0

    t0 = time.time()
    rel_bindings = find_relationship_bindings(diagram["relationships"], nlt)
    t_rel = time.time() - t0

    t0 = time.time()
    dg = dep_graph(nlt)
    t_dg = time.time() - t0

    cov = coverage_summary(matches)
    bind_sum = binding_summary(diagram, class_attr_bindings, rel_bindings)
    diagram_sum = summarise(diagram)
    text_sum = text_features(nlt)
    spacy_sum = spacy_features(nlt)

    # ---- extras A (per-rel-kind coverage), C (sentence stats), E (style), M (warnings)
    rel_kind_rows = _rel_kind_coverage(diagram, rel_bindings)
    sent_rows = _sentence_stats(nlt, dg, matches)
    style_features = _nlt_style_features(nlt, dg)
    parser_warnings = _parser_warnings(diagram)

    # Flatten
    row = {
        "dataset": dataset,
        "id": rec["id"],
        **text_sum,
        **{f"spacy_{k}": v for k, v in spacy_sum.items()},
        **{f"style_{k}": v for k, v in style_features.items()},
        **diagram_sum,
        # Coverage
        "cov_classes_n": cov["classes"]["n"],
        "cov_classes_L1": cov["classes"]["pct_L1"],
        "cov_classes_L2": cov["classes"]["pct_L2"],
        "cov_classes_L3": cov["classes"]["pct_L3"],
        "cov_classes_L4": cov["classes"]["pct_L4"],
        "cov_classes_absent": cov["classes"]["pct_absent"],
        "cov_attrs_n": cov["attributes"]["n"],
        "cov_attrs_L1": cov["attributes"]["pct_L1"],
        "cov_attrs_L2": cov["attributes"]["pct_L2"],
        "cov_attrs_L3": cov["attributes"]["pct_L3"],
        "cov_attrs_L4": cov["attributes"]["pct_L4"],
        "cov_attrs_absent": cov["attributes"]["pct_absent"],
        "cov_enum_n": cov["enum_values"]["n"],
        "cov_enum_absent": cov["enum_values"]["pct_absent"],
        "cov_rel_src_absent": cov["relationships_source"]["pct_absent"],
        "cov_rel_tgt_absent": cov["relationships_target"]["pct_absent"],
        # Binding
        **bind_sum,
        # Timings
        "time_diagram_s": round(t_diagram, 4),
        "time_idx_s": round(t_idx, 4),
        "time_match_s": round(t_match, 4),
        "time_class_attr_s": round(t_ca, 4),
        "time_rel_s": round(t_rel, 4),
        "time_depgraph_s": round(t_dg, 4),
        "n_parser_warnings": len(parser_warnings),
    }
    # Keep the heavy per-record data in a sidecar JSONL.
    sidecar = {
        "dataset": dataset,
        "id": rec["id"],
        "nlt": nlt,
        "puml": puml,
        "diagram": diagram,
        "matches": matches,
        "class_attr_bindings": class_attr_bindings,
        "rel_bindings": rel_bindings,
        "rel_kind_coverage": rel_kind_rows,
        "sentence_stats": sent_rows,
        "style_features": style_features,
        "parser_warnings": parser_warnings,
        "dep_graph_summary": {
            "n_nodes": len(dg["nodes"]),
            "n_edges": len(dg["edges"]),
            "n_noun_chunks": len(dg["noun_chunks"]),
        },
    }
    return row, sidecar


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="kaiser,reference,data_source_3",
                    help="comma-separated subset of kaiser,reference,data_source_3")
    ap.add_argument("--out", default=str(_HERE / "out"),
                    help="output directory")
    ap.add_argument("--limit", type=int, default=None,
                    help="process only the first N records per dataset (for testing)")
    ap.add_argument("--no-cross-ref", action="store_true",
                    help="skip the kaiser↔data_source_3 cross-reference")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
    all_rows: List[Dict[str, Any]] = []
    sidecars: Dict[str, Dict[str, Any]] = {}

    for ds in datasets:
        recs = load_dataset(ds)
        if args.limit:
            recs = recs[: args.limit]
        print(f"[analyze] dataset={ds} records={len(recs)}")
        for i, rec in enumerate(recs, 1):
            t0 = time.time()
            row, sidecar = analyse_record(ds, rec)
            dt = time.time() - t0
            all_rows.append(row)
            sidecars[f"{ds}::{rec['id']}"] = sidecar
            if i % 5 == 0 or i == len(recs):
                print(f"  [{ds}] {i}/{len(recs)} {rec['id']} ({dt:.2f}s)")

    # Per-record wide CSV
    per_record_csv = out_dir / "per_record.csv"
    df = pd.DataFrame(all_rows)
    df.to_csv(per_record_csv, index=False)
    print(f"[analyze] wrote {per_record_csv} ({len(df)} rows)")

    # Per-record sidecar JSONL
    sidecar_path = out_dir / "per_record.jsonl"
    with open(sidecar_path, "w") as f:
        for k, v in sidecars.items():
            f.write(json.dumps(v) + "\n")
    print(f"[analyze] wrote {sidecar_path}")

    # Per-element match CSV (flattened)
    per_element_rows = []
    for k, v in sidecars.items():
        ds, rec_id = k.split("::", 1)
        for c in v["matches"]["classes"]:
            per_element_rows.append({
                "dataset": ds, "id": rec_id, "kind": "class",
                "name": c["name"],
                "L1": c["L1_direct"], "L2": c["L2_lemma"],
                "L3": c["L3_camelcase"], "L4": c["L4_synonym"],
                "absent": c["absent"],
                "sent_indices": ";".join(str(s) for s in c["sent_indices"]),
            })
        for a in v["matches"]["attributes"]:
            per_element_rows.append({
                "dataset": ds, "id": rec_id, "kind": "attribute",
                "name": f'{a["class"]}.{a["name"]}',
                "L1": a["L1_direct"], "L2": a["L2_lemma"],
                "L3": a["L3_camelcase"], "L4": a["L4_synonym"],
                "absent": a["absent"],
                "sent_indices": ";".join(str(s) for s in a["sent_indices"]),
            })
        for e in v["matches"]["enum_values"]:
            per_element_rows.append({
                "dataset": ds, "id": rec_id, "kind": "enum_value",
                "name": f'{e["enum"]}.{e["value"]}',
                "L1": e["L1_direct"], "L2": e["L2_lemma"],
                "L3": e["L3_camelcase"], "L4": e["L4_synonym"],
                "absent": e["absent"],
                "sent_indices": ";".join(str(s) for s in e["sent_indices"]),
            })
        for r in v["matches"]["relationships"]:
            # row per (source, target) endpoint
            per_element_rows.append({
                "dataset": ds, "id": rec_id, "kind": "rel_endpoint",
                "name": f'{r["source"]}-({r["type"]})->{r["target"]}',
                "L1": r["source_L1"], "L2": r["source_L2"],
                "L3": r["source_L3"], "L4": r["source_L4"],
                "absent": r["source_absent"],
                "sent_indices": ";".join(str(s) for s in r["source_sent_indices"]),
            })
            per_element_rows.append({
                "dataset": ds, "id": rec_id, "kind": "rel_endpoint",
                "name": f'{r["source"]}-({r["type"]})->{r["target"]} (tgt)',
                "L1": r["target_L1"], "L2": r["target_L2"],
                "L3": r["target_L3"], "L4": r["target_L4"],
                "absent": r["target_absent"],
                "sent_indices": ";".join(str(s) for s in r["target_sent_indices"]),
            })
    pe_path = out_dir / "per_element_match.csv"
    pd.DataFrame(per_element_rows).to_csv(pe_path, index=False)
    print(f"[analyze] wrote {pe_path} ({len(per_element_rows)} rows)")

    # Extra A: per-relationship-kind coverage
    rel_kind_rows_flat = []
    for k, v in sidecars.items():
        ds, rec_id = k.split("::", 1)
        for r in v["rel_kind_coverage"]:
            rel_kind_rows_flat.append({
                "dataset": ds, "id": rec_id, **r,
            })
    rk_path = out_dir / "rel_kind_coverage.csv"
    pd.DataFrame(rel_kind_rows_flat).to_csv(rk_path, index=False)
    print(f"[analyze] wrote {rk_path} ({len(rel_kind_rows_flat)} rows)")

    # Extra C: sentence-level statistics
    sent_rows_flat = []
    for k, v in sidecars.items():
        ds, rec_id = k.split("::", 1)
        for s in v["sentence_stats"]:
            sent_rows_flat.append({
                "dataset": ds, "id": rec_id, **s,
            })
    ss_path = out_dir / "nlt_sentence_stats.csv"
    pd.DataFrame(sent_rows_flat).to_csv(ss_path, index=False)
    print(f"[analyze] wrote {ss_path} ({len(sent_rows_flat)} rows)")

    # Extra E: NLT style features
    style_rows = []
    for k, v in sidecars.items():
        ds, rec_id = k.split("::", 1)
        style_rows.append({
            "dataset": ds, "id": rec_id,
            **v["style_features"],
        })
    st_path = out_dir / "nlt_style.csv"
    pd.DataFrame(style_rows).to_csv(st_path, index=False)
    print(f"[analyze] wrote {st_path} ({len(style_rows)} rows)")

    # Extra M: parser warnings inventory
    warn_rows = []
    for k, v in sidecars.items():
        ds, rec_id = k.split("::", 1)
        for w in v["parser_warnings"]:
            warn_rows.append({"dataset": ds, "id": rec_id, "warning": w})
    pw_path = out_dir / "parser_warnings.csv"
    pd.DataFrame(warn_rows).to_csv(pw_path, index=False)
    print(f"[analyze] wrote {pw_path} ({len(warn_rows)} rows)")

    # Cross-reference kaiser vs data_source_3
    if not args.no_cross_ref and "kaiser" in datasets and "data_source_3" in datasets:
        cross_rows = []
        for rec_id in sorted({k.split("::", 1)[1] for k in sidecars if k.startswith("kaiser::")}):
            k = f"kaiser::{rec_id}"
            d = f"data_source_3::{rec_id}"
            if k not in sidecars or d not in sidecars:
                continue
            diag_k = sidecars[k]["diagram"]
            diag_d = sidecars[d]["diagram"]
            comp = compare(diag_k, diag_d, "kaiser", "data_source_3")
            cross_rows.append({
                "id": rec_id,
                "kaiser_n_classes": len(diag_k["classes"]),
                "data_source_3_n_classes": len(diag_d["classes"]),
                "kaiser_n_rels": len(diag_k["relationships"]),
                "data_source_3_n_rels": len(diag_d["relationships"]),
                "jaccard_classes": comp["jaccard_classes_kaiser_vs_data_source_3"],
                "jaccard_attributes": comp["jaccard_attributes_kaiser_vs_data_source_3"],
                "jaccard_rels": comp["jaccard_rels_kaiser_vs_data_source_3"],
                "only_in_kaiser_classes": ";".join(comp["diff_classes_kaiser_vs_data_source_3"]["only_in_first"]),
                "only_in_data_source_3_classes": ";".join(comp["diff_classes_kaiser_vs_data_source_3"]["only_in_second"]),
                "only_in_kaiser_rels": ";".join(
                    "|".join(sorted(s)) for s in comp["diff_rels_kaiser_vs_data_source_3"]["only_in_first"]
                ),
                "only_in_data_source_3_rels": ";".join(
                    "|".join(sorted(s)) for s in comp["diff_rels_kaiser_vs_data_source_3"]["only_in_second"]
                ),
            })
        cr_path = out_dir / "cross_dataset.csv"
        pd.DataFrame(cross_rows).to_csv(cr_path, index=False)
        print(f"[analyze] wrote {cr_path} ({len(cross_rows)} rows)")

    print("[analyze] done.")


if __name__ == "__main__":
    main()
