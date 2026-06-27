"""Workflow.metric_runner — score every (source/strategy × model × dataset) cell.

Reads every `Workflow/Results/<source>/<strategy>__<model>/<dataset>.json`
(or `Workflow/Results/<source>/<strategy>/<dataset>.json` for the
rule_based cell which has no model) and appends `scores` to each record.

Writes:
    Workflow/Results/<source>/<strategy>__<model>/<dataset>_scored.json
    Workflow/Results/_summary.csv                     (long format)
    Workflow/Results/_summary.json
    Workflow/Results/_bucket_<dataset>_<element>.csv   (4 tables)
    Workflow/Results/_errors.csv                      (failures)
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

from Metric import (
    BUCKET_LABELS, bucketise, compute, summarise,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.metric_runner")

THIS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = THIS_DIR / "Results"


def _scored_path(raw_path: Path) -> Path:
    return raw_path.with_name(raw_path.stem + "_scored.json")


def _score_record(ref: str, gen: str) -> dict:
    if not gen or not gen.strip():
        return {
            "class_score": 0.0, "attribute_score": 0.0, "association_score": 0.0,
            "parse_warning_ref": [], "parse_warning_gen": [],
            "error": "empty_generated_model",
        }
    try:
        return compute(ref, gen)
    except Exception as exc:
        log.warning("metric compute failed: %s", exc)
        return {
            "class_score": 0.0, "attribute_score": 0.0, "association_score": 0.0,
            "parse_warning_ref": [], "parse_warning_gen": [],
            "error": str(exc),
        }


def _score_one_file(raw_path: Path) -> Path | None:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    scores: list[dict] = []
    for row in records:
        row["scores"] = _score_record(row["reference_model"], row["generated_model"])
        scores.append(row["scores"])
    payload["summary"] = summarise(scores)
    payload["metric_name"] = "metrik-4"

    out = _scored_path(raw_path)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(
        "scored %s (n=%d failed=%d)",
        out.relative_to(RESULTS_DIR),
        len(records), payload["summary"]["class_score"]["failed"],
    )
    return out


def _build_summary_row(payload: dict, element: str) -> dict:
    s = payload["summary"][element]
    return {
        "source":           payload["source"],
        "strategy":         payload["strategy"],
        "model":            payload["model"],
        "model_id":         payload.get("model_id"),
        "dataset":          payload["dataset"],
        "element":          element,
        "n":                s["n"],
        "n_failed":         s["failed"],
        "mean":             s["mean"],
        "std":              s["std"],
        "median":           s["median"],
        "mad":              s["mad"],
        "bucket_0_0.1":     s["buckets"][0],
        "bucket_0.1_0.2":   s["buckets"][1],
        "bucket_0.2_0.3":   s["buckets"][2],
        "bucket_0.3_1.0":   s["buckets"][3],
    }


def _write_cross_summary(scored_files: list[Path]) -> tuple[Path, Path]:
    rows: list[dict] = []
    bucket_rows: dict[tuple[str, str], dict[tuple[str, str, str], dict]] = {}

    for f in scored_files:
        p = json.loads(f.read_text(encoding="utf-8"))
        for element in ("class_score", "attribute_score", "association_score"):
            rows.append(_build_summary_row(p, element))
            bucket_rows.setdefault((p["dataset"], element), {})[
                (p["source"], p["strategy"], p["model"])
            ] = p["summary"][element]

    # 1. Long-format CSV
    out_csv = RESULTS_DIR / "_summary.csv"
    fieldnames = [
        "source", "strategy", "model", "model_id", "dataset", "element",
        "n", "n_failed", "mean", "std", "median", "mad",
        "bucket_0_0.1", "bucket_0.1_0.2", "bucket_0.2_0.3", "bucket_0.3_1.0",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # 2. Bucket tables
    for (dataset, element), strategy_map in bucket_rows.items():
        out_b = RESULTS_DIR / f"_bucket_{dataset}_{element}.csv"
        with out_b.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                "source", "strategy", "model", "n", "n_failed",
                *BUCKET_LABELS,
                "mean", "median",
            ])
            for (source, strategy, model), stats in sorted(strategy_map.items()):
                w.writerow([
                    source, strategy, model, stats["n"], stats["failed"],
                    *stats["buckets"],
                    "" if stats["mean"] is None else f"{stats['mean']:.4f}",
                    "" if stats["median"] is None else f"{stats['median']:.4f}",
                ])

    # 3. Errors
    err_rows: list[dict] = []
    for f in scored_files:
        p = json.loads(f.read_text(encoding="utf-8"))
        for r in p["records"]:
            if r.get("failed") or (r.get("scores") or {}).get("error"):
                err_rows.append({
                    "source":      p["source"],
                    "strategy":    p["strategy"],
                    "model":       p["model"],
                    "dataset":     p["dataset"],
                    "id":          r["id"],
                    "error":       r.get("error") or r.get("scores", {}).get("error", ""),
                    "raw_excerpt": (r.get("raw_excerpt") or "")[:200],
                })
    err_csv = RESULTS_DIR / "_errors.csv"
    with err_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "strategy", "model", "dataset", "id", "error", "raw_excerpt"])
        w.writeheader()
        w.writerows(err_rows)

    # 4. JSON snapshot
    out_json = RESULTS_DIR / "_summary.json"
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    log.info("wrote %s, %s, %s, _bucket_*.csv (×%d), _errors.csv (n=%d)",
             out_csv, out_json, err_csv,
             len(bucket_rows), len(err_rows))
    return out_json, out_csv


def _cell_key_from_path(raw_path: Path) -> tuple[str, str, str, str]:
    """Recover (source, strategy, model, dataset) from the file path.

    Layout: Results/<source>/<strategy>[__<model>]/<dataset>.json
    """
    parts = raw_path.parts
    # Find "Results" in parts (might be <...>/Results/...)
    idx = parts.index("Results")
    source = parts[idx + 1]
    strat_or_strat_model = parts[idx + 2]
    dataset = raw_path.stem
    if "__" in strat_or_strat_model:
        strategy, model = strat_or_strat_model.split("__", 1)
    else:
        strategy, model = strat_or_strat_model, "-"
    return source, strategy, model, dataset


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources", nargs="*", default=None,
                    help="Restrict to these source folders (text2uml-kaiser, etc.)")
    ap.add_argument("--strategies", nargs="*", default=None)
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--datasets", nargs="*", default=None,
                    choices=["kaiser", "reference"])
    args = ap.parse_args(argv)

    if not RESULTS_DIR.is_dir():
        log.error("Results dir not found: %s", RESULTS_DIR)
        return 1

    source_filter = set(args.sources or [])
    strat_filter  = set(args.strategies or [])
    model_filter  = set(args.models or [])
    ds_filter     = set(args.datasets or [])

    scored_files: list[Path] = []
    for source_dir in sorted(p for p in RESULTS_DIR.iterdir() if p.is_dir()):
        if source_dir.name.startswith("_"):
            continue
        source = source_dir.name
        if source_filter and source not in source_filter:
            continue
        for cell_dir in sorted(p for p in source_dir.iterdir() if p.is_dir()):
            parts = cell_dir.name.split("__", 1)
            strategy = parts[0]
            model    = parts[1] if len(parts) == 2 else "-"
            if strat_filter and strategy not in strat_filter:
                continue
            if model_filter and model not in model_filter:
                continue
            for raw in sorted(cell_dir.glob("*.json")):
                if raw.name.endswith("_scored.json"):
                    continue
                ds_name = raw.stem
                if ds_filter and ds_name not in ds_filter:
                    continue
                out = _score_one_file(raw)
                if out is not None:
                    scored_files.append(out)

    if scored_files:
        _write_cross_summary(scored_files)
    else:
        log.warning("no scored files generated")
    return 0


if __name__ == "__main__":
    sys.exit(main())