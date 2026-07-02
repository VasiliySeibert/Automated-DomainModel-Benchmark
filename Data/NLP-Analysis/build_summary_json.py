"""Build the single-file comparison summary JSON.

Reads the per-record wide CSV, the per-element match CSV, the
sidecar JSONL (for cardinality patterns and attribute types), and the
cross-dataset CSV; emits ``out/summary.json`` with a fully self-contained
summary of all comparisons.

Run with::

    PYTHONPATH=. python Data/NLP-Analysis/build_summary_json.py \\
        --in Data/NLP-Analysis/out --out Data/NLP-Analysis/out
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _agg_dataset_overview(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for ds, sub in df.groupby("dataset"):
        out[ds] = {
            "n_records": int(len(sub)),
            "nlt": {
                "words_mean": float(sub["n_words"].mean()),
                "words_median": float(sub["n_words"].median()),
                "words_min": int(sub["n_words"].min()),
                "words_max": int(sub["n_words"].max()),
                "sentences_mean": float(sub["n_sentences"].mean()),
                "sentences_median": float(sub["n_sentences"].median()),
                "type_token_ratio_mean": float(sub["type_token_ratio"].mean()),
            },
            "diagram": {
                "classes_mean": float(sub["n_classes"].mean()),
                "classes_median": float(sub["n_classes"].median()),
                "classes_min": int(sub["n_classes"].min()),
                "classes_max": int(sub["n_classes"].max()),
                "attributes_mean": float(sub["n_attributes"].mean()),
                "enums_mean": float(sub["n_enums"].mean()),
                "relationships_mean": float(sub["n_relationships"].mean()),
                "relationships_median": float(sub["n_relationships"].median()),
                "rels_with_card_pct": float(
                    100 * sub["n_rels_with_card"].sum() / max(1, sub["n_relationships"].sum())
                ),
            },
        }
    return out


def _agg_relationship_type_counts(df: pd.DataFrame) -> Dict[str, Any]:
    rel_cols = [c for c in df.columns if c.startswith("n_rels_")
                and c not in ("n_rels_with_card", "n_rels_with_label", "n_rels_total", "n_rels_bound")]
    out: Dict[str, Any] = {"by_dataset": {}, "total": {}}
    total = Counter()
    for ds, sub in df.groupby("dataset"):
        counts = {c.replace("n_rels_", ""): int(sub[c].sum()) for c in rel_cols}
        out["by_dataset"][ds] = counts
        for k, v in counts.items():
            total[k] += v
    out["total"] = dict(total)
    return out


def _agg_cardinality_patterns(sidecars: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """(src_card, tgt_card) tuple counts, per dataset and total."""
    by_ds: Dict[str, Counter] = defaultdict(Counter)
    for k, sc in sidecars.items():
        ds = sc["dataset"]
        for r in sc["diagram"]["relationships"]:
            key = (r.get("source_card") or "*", r.get("target_card") or "*")
            by_ds[ds][key] += 1
    out = {
        ds: [
            [src, tgt, int(c)]
            for (src, tgt), c in sorted(cnt.items(), key=lambda kv: -kv[1])
        ]
        for ds, cnt in by_ds.items()
    }
    # also a total
    total = Counter()
    for cnt in by_ds.values():
        total.update(cnt)
    out["total"] = [
        [src, tgt, int(c)] for (src, tgt), c in sorted(total.items(), key=lambda kv: -kv[1])
    ]
    return out


def _agg_attribute_type_counts(sidecars: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    c = Counter()
    for sc in sidecars.values():
        for cls in sc["diagram"]["classes"]:
            for a in cls["attributes"]:
                c[a.get("type") or "(untyped)"] += 1
    return dict(c.most_common())


def _agg_lexical_coverage(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    cov_cols = [c for c in df.columns if c.startswith("cov_")]
    out: Dict[str, Dict[str, Any]] = {}
    for ds, sub in df.groupby("dataset"):
        ds_dict: Dict[str, Any] = {}
        for c in cov_cols:
            if sub[c].isna().all():
                continue
            ds_dict[c.replace("cov_", "")] = {
                "mean": float(round(sub[c].mean(), 2)),
                "median": float(round(sub[c].median(), 2)),
            }
        out[ds] = ds_dict
    return out


def _agg_dep_binding(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    cols = ["pct_attrs_bound", "pct_rels_bound", "avg_hop_class_attr", "avg_hop_rel"]
    cols = [c for c in cols if c in df.columns]
    out: Dict[str, Dict[str, Any]] = {}
    for ds, sub in df.groupby("dataset"):
        out[ds] = {c: float(round(sub[c].mean(), 3)) for c in cols}
    return out


def _agg_rel_kind_coverage(rk: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Per dataset, per rel_kind: n, n_bound, pct_bound (mean across records)."""
    out: Dict[str, Dict[str, Any]] = {}
    for ds, sub in rk.groupby("dataset"):
        ds_dict: Dict[str, Any] = {}
        for kind, ksub in sub.groupby("rel_kind"):
            total_n = int(ksub["n"].sum())
            total_bound = int(ksub["n_bound"].sum())
            ds_dict[kind] = {
                "n": total_n,
                "n_bound": total_bound,
                "pct_bound": float(round(100 * total_bound / max(1, total_n), 2)),
            }
        out[ds] = ds_dict
    return out


def _agg_nlt_style(st: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    cols = ["passive_ratio", "hedge_density", "modal_density", "entity_density",
            "modal_count", "hedge_count", "named_entities"]
    cols = [c for c in cols if c in st.columns]
    out: Dict[str, Dict[str, Any]] = {}
    for ds, sub in st.groupby("dataset"):
        out[ds] = {c: float(round(sub[c].mean(), 4)) for c in cols}
    return out


def _agg_sentence_stats(ss: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Mean per-record: sents_per_record, sent_length_mean, sent_with_class_hit, etc."""
    out: Dict[str, Dict[str, Any]] = {}
    cols = ["n_words", "n_class_hits", "n_attr_hits", "n_rel_endpoint_hits"]
    cols = [c for c in cols if c in ss.columns]
    for ds, sub in ss.groupby("dataset"):
        per_rec = sub.groupby(["dataset", "id"]).size().rename("n_sents")
        sents_per_rec = per_rec.mean()
        sent_length = sub["n_words"].mean()
        out[ds] = {
            "sents_per_record_mean": float(round(sents_per_rec, 2)),
            "sentence_length_words_mean": float(round(sent_length, 2)),
            "sentence_length_words_median": float(round(sub["n_words"].median(), 2)),
            "pct_sents_with_class_hit": float(round(
                100 * (sub["n_class_hits"] > 0).mean(), 2)),
            "pct_sents_with_attr_hit": float(round(
                100 * (sub["n_attr_hits"] > 0).mean(), 2)),
            "pct_sents_with_rel_endpoint_hit": float(round(
                100 * (sub["n_rel_endpoint_hits"] > 0).mean(), 2)),
        }
    return out


def _agg_parser_warnings(pw: pd.DataFrame) -> Dict[str, Any]:
    if pw is None or len(pw) == 0:
        return {"total_warnings": 0, "per_dataset": {}, "per_id": {}}
    by_ds = pw.groupby("dataset").size().to_dict()
    by_id = pw.groupby("id").size().sort_values(ascending=False).head(10).to_dict()
    sample = pw["warning"].head(5).tolist()
    return {
        "total_warnings": int(len(pw)),
        "per_dataset": {k: int(v) for k, v in by_ds.items()},
        "top_records": {k: int(v) for k, v in by_id.items()},
        "sample_warnings": sample,
    }


def _agg_cross_dataset(cr: pd.DataFrame) -> Dict[str, Any]:
    if cr is None or len(cr) == 0:
        return {}
    out: Dict[str, Any] = {}
    for col in ["jaccard_classes", "jaccard_attributes", "jaccard_rels"]:
        vals = cr[col].dropna()
        out[col] = {
            "n": int(len(vals)),
            "mean": float(round(vals.mean(), 4)),
            "min": float(vals.min()),
            "max": float(vals.max()),
            "median": float(vals.median()),
            "n_perfect": int((vals == 1.0).sum()),
        }
    diff = cr[cr["jaccard_classes"] < 1.0][
        ["id", "only_in_kaiser_classes", "only_in_data_source_3_classes"]
    ]
    out["records_with_imperfect_classes"] = [
        {
            "id": r["id"],
            "only_in_kaiser": str(r["only_in_kaiser_classes"]).split(";") if pd.notna(r["only_in_kaiser_classes"]) else [],
            "only_in_data_source_3": str(r["only_in_data_source_3_classes"]).split(";") if pd.notna(r["only_in_data_source_3_classes"]) else [],
        }
        for _, r in diff.iterrows()
    ]
    low = cr.nsmallest(5, "jaccard_rels")[
        ["id", "kaiser_n_rels", "data_source_3_n_rels", "jaccard_rels"]
    ]
    out["records_with_lowest_rel_jaccard"] = [
        {
            "id": r["id"],
            "kaiser_n": int(r["kaiser_n_rels"]),
            "data_source_3_n": int(r["data_source_3_n_rels"]),
            "jaccard": float(r["jaccard_rels"]),
        }
        for _, r in low.iterrows()
    ]
    return out


def _agg_lexically_absent_classes(sidecars: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    by_name: Counter = Counter()
    for sc in sidecars.values():
        for c in sc["matches"]["classes"]:
            if c["absent"]:
                by_name[c["name"]] += 1
    return {
        "n_total": int(sum(by_name.values())),
        "n_unique": int(len(by_name)),
        "by_name": dict(by_name.most_common()),
    }


def _agg_extreme_recoverability(df: pd.DataFrame) -> Dict[str, Any]:
    if "pct_rels_bound" not in df.columns:
        return {}
    sorted_df = df.sort_values("pct_rels_bound", ascending=False)
    return {
        "highest_5": [
            {
                "dataset": r["dataset"],
                "id": r["id"],
                "pct_rels_bound": float(round(r["pct_rels_bound"], 1)),
                "pct_attrs_bound": float(round(r["pct_attrs_bound"], 1)),
            }
            for _, r in sorted_df.head(5).iterrows()
        ],
        "lowest_5": [
            {
                "dataset": r["dataset"],
                "id": r["id"],
                "pct_rels_bound": float(round(r["pct_rels_bound"], 1)),
                "pct_attrs_bound": float(round(r["pct_attrs_bound"], 1)),
            }
            for _, r in sorted_df.tail(5).iterrows()
        ],
    }


def _compute_correlation_matrix(df: pd.DataFrame) -> Dict[str, Any]:
    cols = [
        "n_words", "n_sentences",
        "n_classes", "n_attributes", "n_relationships",
        "cov_classes_absent", "cov_attrs_absent",
        "pct_attrs_bound", "pct_rels_bound",
    ]
    cols = [c for c in cols if c in df.columns]
    out: Dict[str, Any] = {"columns": cols, "spearman": {}, "spearman_p": {}}
    for i, a in enumerate(cols):
        out["spearman"][a] = {}
        out["spearman_p"][a] = {}
        for b in cols:
            rho, p = spearmanr(df[a], df[b], nan_policy="omit")
            out["spearman"][a][b] = float(round(rho, 3))
            out["spearman_p"][a][b] = float(round(p, 4))
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def build(in_dir: Path) -> Dict[str, Any]:
    per_record = pd.read_csv(in_dir / "per_record.csv")
    cross = _safe_read_csv(in_dir / "cross_dataset.csv")
    rk = _safe_read_csv(in_dir / "rel_kind_coverage.csv")
    ss = _safe_read_csv(in_dir / "nlt_sentence_stats.csv")
    st = _safe_read_csv(in_dir / "nlt_style.csv")
    pw = _safe_read_csv(in_dir / "parser_warnings.csv")

    sidecars: Dict[str, Dict[str, Any]] = {}
    sidecar_path = in_dir / "per_record.jsonl"
    if sidecar_path.exists():
        with open(sidecar_path) as f:
            for line in f:
                rec = json.loads(line)
                sidecars[f"{rec['dataset']}::{rec['id']}"] = rec

    out: Dict[str, Any] = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": "1.1",
            "datasets": sorted(per_record["dataset"].unique().tolist()),
            "n_records_total": int(len(per_record)),
            "source_files": sorted(p.name for p in in_dir.glob("*.csv"))
                              + sorted(p.name for p in in_dir.glob("*.jsonl")),
        },
        "dataset_overview": _agg_dataset_overview(per_record),
        "relationship_type_counts": _agg_relationship_type_counts(per_record),
        "cardinality_pattern_counts": _agg_cardinality_patterns(sidecars),
        "attribute_type_counts": _agg_attribute_type_counts(sidecars),
        "lexical_coverage": _agg_lexical_coverage(per_record),
        "dep_binding": _agg_dep_binding(per_record),
        "rel_kind_coverage": _agg_rel_kind_coverage(rk) if len(rk) else {},
        "nlt_style": _agg_nlt_style(st) if len(st) else {},
        "sentence_stats": _agg_sentence_stats(ss) if len(ss) else {},
        "parser_warnings": _agg_parser_warnings(pw) if len(pw) else {"total_warnings": 0},
        "correlation_matrix": _compute_correlation_matrix(per_record),
        "cross_dataset_kaiser_vs_data_source_3": _agg_cross_dataset(cross),
        "lexically_absent_classes": _agg_lexically_absent_classes(sidecars),
        "records_with_extreme_recoverability": _agg_extreme_recoverability(per_record),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    args = ap.parse_args()
    in_dir = Path(args.inp)
    out_dir = Path(args.outp)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build(in_dir)
    out_path = out_dir / "summary.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"[summary] wrote {out_path} "
          f"({len(json.dumps(summary)):,} chars, "
          f"{len(summary)} top-level keys)")


if __name__ == "__main__":
    main()
