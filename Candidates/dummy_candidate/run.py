#!/usr/bin/env python3
"""Candidates/dummy_candidate/run.py — driver for the dummy candidate.

Hard-codes the dummy `candidate.py` and chains the three pipeline
steps that live in `Workflow/Benchmark-Workflow/`:

    generate.py   --candidate Candidates/dummy_candidate/candidate.py \\
                   --dataset <dataset> --out <results-dir>/<dataset>.json
    score.py      --in <results-dir>/<dataset>.json --metric <metric>
    visualise.py  --in <results-dir>/<dataset>_scored.json \\
                   --out-dir <out-dir> --metric <metric>

Usage:
    PYTHONPATH=. python Candidates/dummy_candidate/run.py \\
        --dataset kaiser_clean

    PYTHONPATH=. python Candidates/dummy_candidate/run.py \\
        --dataset reference_clean --limit 3

    PYTHONPATH=. python Candidates/dummy_candidate/run.py \\
        --dataset kaiser_clean --metric metrik-4

    # Re-run only the visualiser
    PYTHONPATH=. python Candidates/dummy_candidate/run.py \\
        --dataset kaiser_clean --skip-generate --skip-score

Metric selection:
    Resolution order:
      1. --metric on the CLI.
      2. Candidates/dummy_candidate/metric.json
         ({"default_metric": "metrik-1"} — ships with the dummy).
      3. Project default: metrik-4.

Output layout (under --results-dir, default Workflow/Results/dummy_candidate/):
    <results-dir>/<dataset>.json         # step 1: raw generate output
    <results-dir>/<dataset>_scored.json  # step 2: scored
    <out-dir>/_summary.csv               # step 3: aggregation table
    <out-dir>/_summary.json              # step 3: aggregation table (json)
    <out-dir>/_bucket_<dataset>_<element>_<metric>.csv
    <out-dir>/_errors.csv                # step 3: failure log
    <out-dir>/heatmap_<dataset>_<element>_<metric>.png
    # Default: <out-dir> == <results-dir> so every artefact lives
    # inside Workflow/Results/dummy_candidate/.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import time
from pathlib import Path


CANDIDATE_ID = "dummy_candidate"
THIS_DIR = Path(__file__).resolve().parent          # Candidates/dummy_candidate
REPO_ROOT = THIS_DIR.parent.parent                   # repo root
WORKFLOW_PKG = REPO_ROOT / "Workflow" / "Benchmark-Workflow"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import domain_model_metrics BEFORE any Workflow/ file loads (avoids the
# upstream Workflow package shadow issue described in
# Workflow/Benchmark-Workflow/README.md).
import domain_model_metrics  # noqa: F401

from Metric import METRIC_NAMES


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Candidates.dummy_candidate.run")


DEFAULT_METRIC = "metrik-4"


def _load_step(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _resolve_metric(cli_metric: str | None) -> tuple[str, str]:
    """Pick the metric.

    Returns (metric, source) where source is one of:
      "cli", "candidate_metric.json", "project_default".
    """
    if cli_metric:
        return cli_metric, "cli"

    metric_file = THIS_DIR / "metric.json"
    if metric_file.is_file():
        try:
            cfg = json.loads(metric_file.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("could not read %s: %s", metric_file, exc)
        else:
            m = cfg.get("default_metric")
            if m:
                if m not in METRIC_NAMES:
                    raise SystemExit(
                        f"{metric_file} declares default_metric={m!r} "
                        f"which is not in {METRIC_NAMES}"
                    )
                return m, "candidate_metric.json"

    return DEFAULT_METRIC, "project_default"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True,
                    choices=["kaiser_clean", "reference_clean",
                             "data-source-1", "data-source-2"],
                    help="Dataset name (or data-source-N alias).")
    ap.add_argument("--results-dir", default=None,
                    help="Directory for the JSONs and aggregator outputs. "
                         "Default: Workflow/Results/dummy_candidate/")
    ap.add_argument("--out-dir", default=None,
                    help="Directory for visualiser outputs "
                         "(_summary.csv, _bucket_*.csv, _errors.csv, "
                         "heatmap_*.png). Default: same as --results-dir.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Run only the first N records.")
    ap.add_argument("--metric", default=None, choices=METRIC_NAMES,
                    help="Metric to score with. Default: read from "
                         "Candidates/dummy_candidate/metric.json, else metrik-4.")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--skip-score", action="store_true")
    ap.add_argument("--skip-visualise", action="store_true")
    args = ap.parse_args(argv)

    candidate_path = THIS_DIR / "candidate.py"

    metric, metric_source = _resolve_metric(args.metric)

    results_dir = (
        Path(args.results_dir).resolve() if args.results_dir
        else REPO_ROOT / "Workflow" / "Results" / CANDIDATE_ID
    )
    out_dir = (
        Path(args.out_dir).resolve() if args.out_dir
        else results_dir
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_json = results_dir / f"{args.dataset}.json"
    scored_json = results_dir / f"{args.dataset}_scored.json"

    print("=" * 72)
    print(f"Automated DomainModel Benchmark — driver for {CANDIDATE_ID}")
    print("=" * 72)
    print(f"  Candidate    : {candidate_path}")
    print(f"  Dataset      : {args.dataset}")
    print(f"  Metric       : {metric}  (source: {metric_source})")
    print(f"  Results dir  : {results_dir}")
    print(f"  Output dir   : {out_dir}")
    if args.limit:
        print(f"  Limit        : first {args.limit} records")
    print(f"  Steps        : "
          f"{'generate ' if not args.skip_generate else '(skip)generate '}"
          f"{'score ' if not args.skip_score else '(skip)score '}"
          f"{'visualise' if not args.skip_visualise else '(skip)visualise'}")
    print("=" * 72)

    generate = _load_step("_wf_generate", WORKFLOW_PKG / "generate.py")
    score    = _load_step("_wf_score",    WORKFLOW_PKG / "score.py")
    visualise= _load_step("_wf_visualise",WORKFLOW_PKG / "visualise.py")

    t_total = time.time()

    if not args.skip_generate:
        t0 = time.time()
        rc = generate.main([
            "--candidate", str(candidate_path),
            "--dataset",   args.dataset,
            "--out",       str(raw_json),
            *(["--limit", str(args.limit)] if args.limit else []),
        ])
        print(f"\n[generate]  done in {time.time()-t0:.1f}s (rc={rc}) → {raw_json}")
        if rc != 0:
            return rc

    if not args.skip_score:
        if not raw_json.exists():
            log.error("score: input %s missing; run generate first", raw_json)
            return 1
        t0 = time.time()
        rc = score.main([
            "--in",     str(raw_json),
            "--metric", metric,
        ])
        print(f"\n[score]     done in {time.time()-t0:.1f}s (rc={rc}) → {scored_json}")
        if rc != 0:
            return rc

    if not args.skip_visualise:
        if not scored_json.exists():
            log.error("visualise: input %s missing; run score first", scored_json)
            return 1
        t0 = time.time()
        rc = visualise.main([
            "--in",      str(scored_json),
            "--out-dir", str(out_dir),
            "--metric",  metric,
        ])
        print(f"\n[visualise] done in {time.time()-t0:.1f}s (rc={rc}) → {out_dir}")
        if rc != 0:
            return rc

    print(f"\n[run] DONE in {time.time()-t_total:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
