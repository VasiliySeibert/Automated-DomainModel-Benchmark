#!/usr/bin/env python3
"""Workflow/Benchmark-Workflow/score.py — step 2 of the benchmark pipeline.

Reads the JSON produced by `Workflow/Benchmark-Workflow/generate.py`,
runs metrik-4 on every (reference, generated) pair, and writes a
`<stem>_scored.json` alongside the input. No aggregation — that's
`Workflow/Benchmark-Workflow/visualise.py`.

Usage:
    PYTHONPATH=. python Workflow/Benchmark-Workflow/score.py \
        --in Workflow/Results/dummy_candidate/kaiser_clean.json

    PYTHONPATH=. python Workflow/Benchmark-Workflow/score.py \
        --in 'Workflow/Results/dummy_candidate/kaiser_clean.json' --out my_scored.json

Output JSON schema (additions to the input):
    records[i].scores = {
        "class_score":        float,
        "attribute_score":    float,
        "association_score":  float,
        "parse_warning_ref":  list[str],
        "parse_warning_gen":  list[str],
        "error":              str | None
    }
    summary = {
        "class_score":      {mean, std, median, mad, n, buckets, failed},
        "attribute_score":  {...},
        "association_score":{...}
    }
    metric_name = "metrik-4"
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Metric import METRIC_NAMES, compute, summarise


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.score")


def _score_pair(ref: str, gen: str, metric_name: str) -> dict:
    if not gen or not gen.strip():
        return {
            "class_score":       0.0,
            "attribute_score":   0.0,
            "association_score": 0.0,
            "parse_warning_ref": [],
            "parse_warning_gen": [],
            "error":             "empty_generated_model",
        }
    try:
        return compute(ref, gen, metric_name=metric_name)
    except Exception as exc:
        log.warning("metric %s compute failed: %s", metric_name, exc)
        return {
            "class_score":       0.0,
            "attribute_score":   0.0,
            "association_score": 0.0,
            "parse_warning_ref": [],
            "parse_warning_gen": [],
            "error":             str(exc),
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", required=True,
                    help="Input JSON produced by Workflow/Benchmark-Workflow/generate.py.")
    ap.add_argument("--out", default=None,
                    help="Output JSON path. Default: <stem>_scored.json next to input.")
    ap.add_argument("--metric", default="metrik-4", choices=METRIC_NAMES,
                    help="Which metrik from domain-model-metrics to use "
                         "(default: metrik-4).")
    args = ap.parse_args(argv)

    in_path = Path(args.in_path).resolve()
    out_path = (
        Path(args.out).resolve() if args.out
        else in_path.with_name(in_path.stem + "_scored.json")
    )
    log.info("scoring %s → %s (metric=%s)", in_path, out_path, args.metric)

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    score_list: list[dict] = []
    for i, row in enumerate(records, 1):
        s = _score_pair(row["reference"], row["generated"], args.metric)
        row["scores"] = s
        score_list.append(s)
        if i % 10 == 0 or i == len(records):
            log.info("  scored %d/%d", i, len(records))

    payload["summary"] = summarise(score_list)
    payload["metric_name"] = args.metric

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info(
        "wrote %s (n=%d, failed=%d)",
        out_path, len(records),
        payload["summary"]["class_score"]["failed"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())