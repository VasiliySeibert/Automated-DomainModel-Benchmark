#!/usr/bin/env python3
"""Workflow/run_all.py — chains generate → score → visualise.

Usage:
    PYTHONPATH=. python Workflow/run_all.py \
        --candidate Candidates/dummy_candidate/candidate.py \
        --dataset kaiser_clean

    PYTHONPATH=. python Workflow/run_all.py \
        --candidate Candidates/dummy_candidate/candidate.py \
        --dataset reference_clean \
        --results-dir Workflow/Results/dummy_candidate \
        --limit 3 \
        --skip-visualise

Metric selection (--metric):
    Resolution order:
      1. --metric on the CLI.
      2. `<candidate_folder>/metric.json` (`{"default_metric": "..."}`).
         Only consulted if --candidate points to a folder or to a file
         inside a candidate folder.
      3. Project default: metrik-4.

Output layout (under --results-dir, default Workflow/Results/<candidate-name>/):
    <results-dir>/<dataset>.json         # step 1: raw generate output
    <results-dir>/<dataset>_scored.json  # step 2: scored
    _summary.csv, _bucket_*.csv, ...     # step 3: aggregations + heatmaps
                                          # (always written under --out-dir,
                                          #  default Workflow/Results)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import domain_model_metrics BEFORE any Workflow/ file loads (avoids the
# upstream Workflow package shadow issue described in Workflow/README.md).
import domain_model_metrics  # noqa: F401

from Metric import METRIC_NAMES


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.run_all")


DEFAULT_METRIC = "metrik-4"


def _load_step(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _candidate_name(candidate_path: Path) -> str:
    """Derive a filesystem-friendly name for the candidate."""
    name = candidate_path.resolve().name
    if name == "candidate.py":
        name = candidate_path.resolve().parent.name
    if name.endswith(".py"):
        name = name[:-3]
    return name.replace(" ", "_")


def _candidate_folder(candidate_path: Path) -> Path | None:
    """Return the candidate folder if --candidate points into one.

    A folder is detected if --candidate points to a folder, or to a file
    whose parent contains a `metric.json` or `README.md` (heuristic: any
    sibling config file at the folder level).
    """
    p = candidate_path.resolve()
    if p.is_dir():
        return p
    if p.is_file():
        parent = p.parent
        if (parent / "metric.json").exists() or (parent / "README.md").exists():
            return parent
    return None


def _resolve_metric(cli_metric: str | None,
                    candidate_path: Path) -> tuple[str, str]:
    """Pick the metric.

    Returns (metric, source) where source is one of:
      "cli", "candidate_metric.json", "project_default".
    """
    if cli_metric:
        return cli_metric, "cli"

    folder = _candidate_folder(candidate_path)
    if folder is not None:
        metric_file = folder / "metric.json"
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
    ap.add_argument("--candidate", required=True,
                    help="Path to candidate.py OR to a folder containing it.")
    ap.add_argument("--dataset", required=True,
                    choices=["kaiser_clean", "reference_clean",
                             "data-source-1", "data-source-2"],
                    help="Dataset name (or data-source-N alias).")
    ap.add_argument("--results-dir", default=None,
                    help="Directory for per-cell JSONs. "
                         "Default: Workflow/Results/<candidate-name>/")
    ap.add_argument("--out-dir", default=None,
                    help="Directory for cross-candidate aggregations. "
                         "Default: parent of --results-dir.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Run only the first N records.")
    ap.add_argument("--metric", default=None, choices=METRIC_NAMES,
                    help="Metric to score with. Default: read from "
                         "<candidate>/metric.json, else metrik-4.")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--skip-score", action="store_true")
    ap.add_argument("--skip-visualise", action="store_true")
    args = ap.parse_args(argv)

    candidate_path = Path(args.candidate).resolve()
    cand_name = _candidate_name(candidate_path)

    metric, metric_source = _resolve_metric(args.metric, candidate_path)

    results_dir = (
        Path(args.results_dir).resolve() if args.results_dir
        else REPO_ROOT / "Workflow" / "Results" / cand_name
    )
    out_dir = (
        Path(args.out_dir).resolve() if args.out_dir
        else results_dir.parent
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_json = results_dir / f"{args.dataset}.json"
    scored_json = results_dir / f"{args.dataset}_scored.json"

    print("=" * 72)
    print("Automated DomainModel Benchmark — run_all")
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

    generate = _load_step("_wf_generate", REPO_ROOT / "Workflow" / "generate.py")
    score    = _load_step("_wf_score",    REPO_ROOT / "Workflow" / "score.py")
    visualise= _load_step("_wf_visualise",REPO_ROOT / "Workflow" / "visualise.py")

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

    print(f"\n[run_all] DONE in {time.time()-t_total:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())