#!/usr/bin/env python3
"""One-shot driver for the full benchmark.

Runs:
    1. Orchestrator (every (source, strategy, model, dataset) cell)
    2. Metric runner (score every cell with metrik-4, write bucket tables)

Pre-requisite:
    source .venv/bin/activate   (caller does this before running us)

Usage:
    PYTHONPATH=. python Workflow/run_full.py
    PYTHONPATH=. python Workflow/run_full.py --smoke
    PYTHONPATH=. python Workflow/run_full.py --strategies text2uml-kaiser
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import domain_model_metrics FIRST so its Workflow path injection runs
# before any of our Workflow/ files get loaded.
import domain_model_metrics  # noqa: F401


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _print_banner(args) -> None:
    from Candidates.registry import all_specs, SOURCE_DIRS

    cfg = _load("_wf_cfg", REPO_ROOT / "Workflow" / "config_loader.py")
    n_llm_specs = sum(1 for s in all_specs() if s.uses_llm)
    n_rule_specs = sum(1 for s in all_specs() if not s.uses_llm)
    models = args.models or cfg.model_shorts()
    datasets = args.datasets or cfg.datasets()
    print("=" * 72)
    print("Automated DomainModel Benchmark")
    print("=" * 72)
    print(f"  Source groups : {', '.join(sorted(SOURCE_DIRS))}")
    print(f"  Strategies    : {n_llm_specs} LLM + {n_rule_specs} rule-based")
    print(f"                 ({', '.join(s.strategy for s in all_specs())})")
    print(f"  Models        : {', '.join(models)}")
    print(f"  Datasets      : {', '.join(datasets)}")
    print(f"  Mode          : {'SMOKE' if args.smoke else 'FULL'}")
    if args.limit:
        print(f"  Per-dataset limit: {args.limit} records")
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strategies", nargs="*", default=None,
                    help="Source groups (text2uml-kaiser, AutomatedDomainModelling-zenodo, ai4se_benchmarkPaper)")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--skip-orchestrator", action="store_true")
    ap.add_argument("--skip-metric", action="store_true")
    args = ap.parse_args(argv)

    _print_banner(args)

    orchestrator = _load("_wf_orchestrator", REPO_ROOT / "Workflow" / "orchestrator.py")
    metric_runner = _load("_wf_metric", REPO_ROOT / "Workflow" / "metric_runner.py")

    if not args.skip_orchestrator:
        orch_args = [
            *(["--strategies", *args.strategies] if args.strategies else []),
            *(["--models", *args.models] if args.models else []),
            *(["--datasets", *args.datasets] if args.datasets else []),
            *(["--limit", str(args.limit)] if args.limit else []),
            *(["--smoke"] if args.smoke else []),
        ]
        t0 = time.time()
        rc = orchestrator.main(orch_args)
        print(f"\n[orchestrator] done in {time.time()-t0:.1f}s (rc={rc})")
        if rc != 0:
            return rc

    if not args.skip_metric:
        metric_args = [
            *(["--strategies", *args.strategies] if args.strategies else []),
            *(["--models", *args.models] if args.models else []),
            *(["--datasets", *args.datasets] if args.datasets else []),
        ]
        t0 = time.time()
        rc = metric_runner.main(metric_args)
        print(f"\n[metric_runner] done in {time.time()-t0:.1f}s (rc={rc})")
        if rc != 0:
            return rc

    print("\n[run_full] DONE")
    print("Outputs:")
    print("  Workflow/Results/_summary.csv               (long format)")
    print("  Workflow/Results/_bucket_<dataset>_<element>.csv   (4 tables)")
    print("  Workflow/Results/_errors.csv                (failures)")
    print("  Workflow/Notebooks/walkthrough.ipynb        (visualisation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())