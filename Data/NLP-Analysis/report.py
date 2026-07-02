"""Reporting: aggregate statistics, charts, summary.md.

Run with: python report.py --in Data/NLP-Analysis/out --out Data/NLP-Analysis/out
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def charts_dir(out_dir: Path) -> Path:
    p = out_dir / "charts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def chart_nlt_vs_classes(df: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colours = {"kaiser": "tab:blue", "reference": "tab:orange",
               "data_source_3": "tab:green"}
    for ds, sub in df.groupby("dataset"):
        ax.scatter(sub["n_words"], sub["n_classes"],
                   alpha=0.7, label=ds, color=colours.get(ds, "grey"))
    ax.set_xlabel("NLT word count")
    ax.set_ylabel("# classes in diagram")
    ax.set_title("NLT length vs diagram size (one dot = one record)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def chart_rel_type_distribution(df: pd.DataFrame, out: Path):
    rel_cols = [c for c in df.columns if c.startswith("n_rels_")
                and c not in ("n_rels_with_card", "n_rels_with_label")]
    agg = df.groupby("dataset")[rel_cols].mean().round(2)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    agg.T.plot(kind="bar", ax=ax, color=["tab:blue", "tab:orange", "tab:green"])
    ax.set_ylabel("mean # relationships per record")
    ax.set_title("Relationship-type distribution by dataset")
    ax.legend(title="dataset", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def chart_attr_lexical_coverage(df: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bins = list(range(0, 110, 10))
    for ds, sub in df.groupby("dataset"):
        ax.hist(sub["cov_attrs_L1"].fillna(0), bins=bins, alpha=0.5, label=ds)
    ax.set_xlabel("% of attributes directly lexically present in NLT (L1)")
    ax.set_ylabel("# records")
    ax.set_title("Lexical coverage of attributes (L1, direct match)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def chart_cross_dataset_jaccard(cr: pd.DataFrame, out: Path):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, col, title in zip(
        axes,
        ["jaccard_classes", "jaccard_attributes", "jaccard_rels"],
        ["Classes", "Attributes", "Relationships"],
    ):
        ax.boxplot([cr[col].dropna()], tick_labels=[title])
        ax.set_ylim(-0.05, 1.05)
        ax.set_ylabel("Jaccard")
        ax.set_title(f"kaiser vs data_source_3 — {title}")
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def chart_pct_bound(df: pd.DataFrame, out: Path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, col, title in zip(
        axes,
        ["pct_attrs_bound", "pct_rels_bound"],
        ["Attributes syntactically bound\nto their class in the NLT",
         "Relationships recoverable\nfrom a sentence in the NLT"],
    ):
        for ds, sub in df.groupby("dataset"):
            ax.hist(sub[col].fillna(0), bins=20, alpha=0.5, label=ds)
        ax.set_xlabel("% bound / recoverable")
        ax.set_ylabel("# records")
        ax.set_title(title)
        ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def chart_correlation_heatmap(df: pd.DataFrame, out: Path):
    """Spearman correlation heatmap of NLT length, diagram size, coverage,
    and binding percentages."""
    cols = [
        "n_words", "n_sentences",
        "n_classes", "n_attributes", "n_relationships",
        "cov_classes_absent", "cov_attrs_absent",
        "pct_attrs_bound", "pct_rels_bound",
    ]
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 2:
        return
    corr = df[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(cols)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}",
                    ha="center", va="center",
                    color="white" if abs(corr.values[i, j]) > 0.5 else "black",
                    fontsize=8)
    fig.colorbar(im, ax=ax, label="Spearman ρ")
    ax.set_title("Spearman correlation: NLT length, diagram size, coverage, binding")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def make_summary(df: pd.DataFrame, cr: pd.DataFrame, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# NLP Analysis — Summary\n"]

    # Overview table
    lines.append("## 1. Per-dataset overview\n")
    agg = df.groupby("dataset").agg(
        n=("id", "count"),
        words_mean=("n_words", "mean"),
        words_med=("n_words", "median"),
        sents_mean=("n_sentences", "mean"),
        classes_mean=("n_classes", "mean"),
        attrs_mean=("n_attributes", "mean"),
        rels_mean=("n_relationships", "mean"),
        rels_median=("n_relationships", "median"),
    ).round(2)
    lines.append(agg.to_markdown())
    lines.append("")

    # Relationship-type breakdown
    rel_cols = [c for c in df.columns if c.startswith("n_rels_")
                and c not in ("n_rels_with_card", "n_rels_with_label")]
    rel_agg = df.groupby("dataset")[rel_cols].mean().round(2)
    lines.append("## 2. Mean relationship-type counts per record\n")
    lines.append(rel_agg.to_markdown())
    lines.append("")

    # Cardinality coverage
    rels = df.groupby("dataset")[["n_relationships", "n_rels_with_card"]].mean().round(2)
    rels["pct_with_card"] = (100 * rels["n_rels_with_card"] / rels["n_relationships"]).round(2)
    lines.append("## 3. Multiplicity coverage\n")
    lines.append(rels.to_markdown())
    lines.append("")

    # Lexical coverage table
    cov_cols = ["cov_classes_L1", "cov_classes_L2", "cov_classes_L3", "cov_classes_L4",
                "cov_classes_absent",
                "cov_attrs_L1", "cov_attrs_L2", "cov_attrs_L3", "cov_attrs_L4",
                "cov_attrs_absent",
                "cov_enum_L1" if "cov_enum_L1" in df.columns else "cov_enum_absent",
                "cov_rel_src_absent", "cov_rel_tgt_absent"]
    cov_cols = [c for c in cov_cols if c in df.columns]
    cov_agg = df.groupby("dataset")[cov_cols].mean().round(2)
    lines.append("## 4. Lexical coverage (mean per record, %)\n")
    lines.append("L1=direct, L2=lemma/plural, L3=camelCase-split, L4=WordNet synonym, absent=none.\n")
    lines.append(cov_agg.to_markdown())
    lines.append("")

    # Dependency-binding
    bind = df.groupby("dataset")[
        ["pct_attrs_bound", "pct_rels_bound",
         "avg_hop_class_attr", "avg_hop_rel"]
    ].mean().round(3)
    lines.append("## 5. Dependency-graph binding (mean per record)\n")
    lines.append(bind.to_markdown())
    lines.append("")

    # Cross-dataset
    if cr is not None and len(cr) > 0:
        lines.append("## 6. Cross-dataset: kaiser vs data_source_3 (same 45 NLTs)\n")
        des = cr[["jaccard_classes", "jaccard_attributes", "jaccard_rels"]].describe().round(3)
        lines.append(des.to_markdown())
        lines.append("")
        lines.append("Records with imperfect class Jaccard:\n")
        diff_cls = cr[cr["jaccard_classes"] < 1.0][
            ["id", "only_in_kaiser_classes", "only_in_data_source_3_classes"]
        ]
        if len(diff_cls) == 0:
            lines.append("- (none — all 45 records have identical class sets)\n")
        else:
            lines.append(diff_cls.to_markdown())
        lines.append("")

        lines.append("Records with the lowest relationship Jaccard:\n")
        low = cr.nsmallest(5, "jaccard_rels")[
            ["id", "kaiser_n_rels", "data_source_3_n_rels", "jaccard_rels"]
        ]
        lines.append(low.to_markdown())
        lines.append("")

    out_path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    args = ap.parse_args()
    in_dir = Path(args.inp)
    out_dir = Path(args.outp)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_record = pd.read_csv(in_dir / "per_record.csv")
    chart_nlt_vs_classes(per_record, charts_dir(out_dir) / "chart_nlt_vs_classes.png")
    chart_rel_type_distribution(per_record, charts_dir(out_dir) / "chart_rel_type_distribution.png")
    chart_attr_lexical_coverage(per_record, charts_dir(out_dir) / "chart_attr_lexical_coverage.png")
    chart_pct_bound(per_record, charts_dir(out_dir) / "chart_pct_bound.png")
    chart_correlation_heatmap(per_record, charts_dir(out_dir) / "chart_correlation_heatmap.png")
    cr_path = in_dir / "cross_dataset.csv"
    cr = pd.read_csv(cr_path) if cr_path.exists() else None
    if cr is not None and len(cr) > 0:
        chart_cross_dataset_jaccard(cr, charts_dir(out_dir) / "chart_cross_dataset_jaccard.png")
    make_summary(per_record, cr, out_dir / "summary.md")
    print(f"[report] wrote charts and {out_dir/'summary.md'}")


if __name__ == "__main__":
    main()
