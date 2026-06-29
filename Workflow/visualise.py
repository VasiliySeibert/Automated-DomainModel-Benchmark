#!/usr/bin/env python3
"""Workflow/visualise.py — step 3 of the benchmark pipeline.

Reads scored JSONs (produced by `Workflow/score.py`), aggregates
them, and writes:

    <out-dir>/_summary.csv                        (long format)
    <out-dir>/_summary.json
    <out-dir>/_bucket_<dataset>_<element>_<metric>.csv   (one per dataset × element)
    <out-dir>/_errors.csv                         (failures)
    <out-dir>/heatmap_<dataset>_<element>_<metric>.png   (per dataset × element)

Usage:
    PYTHONPATH=. python Workflow/visualise.py \\
        --in 'Workflow/Results/*/*_scored.json' \\
        --out-dir Workflow/Results \\
        --metric metrik-1

    # Multiple inputs supported as repeatable flags or glob:
    PYTHONPATH=. python Workflow/visualise.py \\
        --in Workflow/Results/dummy_candidate/kaiser_scored.json \\
        --in Workflow/Results/dummy_candidate/reference_scored.json \\
        --out-dir Workflow/Results \\
        --metric metrik-1

Note: --metric is REQUIRED. Every input must be a scored JSON produced
by `Workflow/score.py --metric <name>` with the same metric. Mixing
metrics in one --out-dir is rejected.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import logging
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Metric import BUCKET_LABELS, METRIC_NAMES


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.visualise")


ELEMENTS = ("class_score", "attribute_score", "association_score")


def _expand_inputs(patterns: Iterable[str]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for pat in patterns:
        for m in glob.glob(pat):
            p = Path(m).resolve()
            if p.is_file() and p not in seen:
                seen.add(p)
                out.append(p)
    return sorted(out)


def _build_summary_row(payload: dict, element: str) -> dict:
    s = payload["summary"][element]
    return {
        "metric":            payload.get("metric_name", ""),
        "candidate":         payload.get("candidate", ""),
        "dataset":           payload["dataset"],
        "element":           element,
        "n":                 s["n"],
        "n_failed":          s["failed"],
        "mean":              s["mean"],
        "std":               s["std"],
        "median":            s["median"],
        "mad":               s["mad"],
        "bucket_0_0.1":      s["buckets"][0],
        "bucket_0.1_0.2":    s["buckets"][1],
        "bucket_0.2_0.3":    s["buckets"][2],
        "bucket_0.3_1.0":    s["buckets"][3],
    }


def _validate_metrics(scored_files: list[Path], requested: str) -> None:
    """Reject mixed-metric inputs and inputs that disagree with --metric."""
    mismatched: list[tuple[Path, str]] = []
    for f in scored_files:
        p = json.loads(f.read_text(encoding="utf-8"))
        m = p.get("metric_name")
        if m is None:
            mismatched.append((f, "<missing metric_name>"))
        elif m != requested:
            mismatched.append((f, m))
    if mismatched:
        details = "\n".join(f"  {f} -> {m}" for f, m in mismatched)
        raise SystemExit(
            f"--metric={requested} but inputs use different metrics:\n{details}\n"
            f"Re-run Workflow/score.py with --metric={requested} for each input."
        )


def _write_long_summary(scored_files: list[Path], out_dir: Path) -> Path:
    rows: list[dict] = []
    for f in scored_files:
        p = json.loads(f.read_text(encoding="utf-8"))
        for el in ELEMENTS:
            rows.append(_build_summary_row(p, el))
    out = out_dir / "_summary.csv"
    fields = [
        "metric", "candidate", "dataset", "element", "n", "n_failed",
        "mean", "std", "median", "mad",
        "bucket_0_0.1", "bucket_0.1_0.2", "bucket_0.2_0.3", "bucket_0.3_1.0",
    ]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    (out_dir / "_summary.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    return out


def _write_bucket_tables(scored_files: list[Path], out_dir: Path,
                         metric: str) -> list[Path]:
    """One CSV per (dataset, element). Rows are one per candidate."""
    bucket_rows: dict[tuple[str, str], dict[str, dict]] = {}
    for f in scored_files:
        p = json.loads(f.read_text(encoding="utf-8"))
        cand = p.get("candidate", "<unknown>")
        for el in ELEMENTS:
            bucket_rows.setdefault((p["dataset"], el), {})[cand] = p["summary"][el]

    written: list[Path] = []
    for (dataset, element), cand_map in bucket_rows.items():
        out = out_dir / f"_bucket_{dataset}_{element}_{metric}.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["candidate", "n", "n_failed", *BUCKET_LABELS, "mean", "median"])
            for cand, stats in sorted(cand_map.items()):
                w.writerow([
                    cand, stats["n"], stats["failed"],
                    *stats["buckets"],
                    "" if stats["mean"] is None else f"{stats['mean']:.4f}",
                    "" if stats["median"] is None else f"{stats['median']:.4f}",
                ])
        written.append(out)
    return written


def _write_errors(scored_files: list[Path], out_dir: Path) -> Path:
    rows: list[dict] = []
    for f in scored_files:
        p = json.loads(f.read_text(encoding="utf-8"))
        for r in p["records"]:
            if r.get("failed") or (r.get("scores") or {}).get("error"):
                rows.append({
                    "candidate":   p.get("candidate", ""),
                    "dataset":     p["dataset"],
                    "id":          r["id"],
                    "error":       (r.get("error")
                                    or (r.get("scores") or {}).get("error", "")),
                    "raw_excerpt": (r.get("raw_excerpt") or "")[:200],
                })
    out = out_dir / "_errors.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["candidate", "dataset", "id", "error", "raw_excerpt"],
        )
        w.writeheader()
        w.writerows(rows)
    return out


def _write_heatmaps(scored_files: list[Path], out_dir: Path,
                    metric: str) -> list[Path]:
    """One PNG per (dataset, element). Each row is a candidate; columns are buckets."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:
        log.warning("matplotlib not available (%s); skipping heatmaps", exc)
        return []

    bucket_rows: dict[tuple[str, str], dict[str, list[int]]] = {}
    for f in scored_files:
        p = json.loads(f.read_text(encoding="utf-8"))
        cand = p.get("candidate", "<unknown>")
        for el in ELEMENTS:
            key = (p["dataset"], el)
            stats = p["summary"][el]
            bucket_rows.setdefault(key, {})[cand] = list(stats["buckets"])

    written: list[Path] = []
    for (dataset, element), cand_map in bucket_rows.items():
        if not cand_map:
            continue
        cands = sorted(cand_map.keys())
        data = np.array([cand_map[c] for c in cands], dtype=float)
        fig, ax = plt.subplots(figsize=(6, max(2, 0.5 * len(cands) + 1)))
        im = ax.imshow(data, aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(BUCKET_LABELS)))
        ax.set_xticklabels(BUCKET_LABELS, rotation=30, ha="right")
        ax.set_yticks(range(len(cands)))
        ax.set_yticklabels(cands)
        ax.set_title(f"{dataset} — {element} ({metric})")
        for i in range(len(cands)):
            for j in range(len(BUCKET_LABELS)):
                ax.text(j, i, int(data[i, j]),
                        ha="center", va="center",
                        color="white" if data[i, j] < data.max() * 0.6 else "black")
        fig.colorbar(im, ax=ax, label="record count")
        out = out_dir / f"heatmap_{dataset}_{element}_{metric}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        plt.close(fig)
        written.append(out)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inputs", action="append", required=True,
                    help="Scored JSON path or glob. Repeatable.")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--metric", required=True, choices=METRIC_NAMES,
                    help="Metric used to produce the inputs. Bucket tables "
                         "and heatmaps are suffixed with this name.")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = _expand_inputs(args.inputs)
    if not files:
        log.error("no input files matched: %s", args.inputs)
        return 1
    _validate_metrics(files, args.metric)
    log.info("aggregating %d scored JSONs (metric=%s)", len(files), args.metric)

    summary_csv = _write_long_summary(files, out_dir)
    bucket_csvs = _write_bucket_tables(files, out_dir, args.metric)
    errors_csv = _write_errors(files, out_dir)
    heatmaps = _write_heatmaps(files, out_dir, args.metric)

    log.info("wrote %s", summary_csv)
    log.info("wrote %d bucket table(s)", len(bucket_csvs))
    log.info("wrote %s", errors_csv)
    log.info("wrote %d heatmap(s) (PNG)", len(heatmaps))
    return 0


if __name__ == "__main__":
    sys.exit(main())