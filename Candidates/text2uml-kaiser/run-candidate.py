#!/usr/bin/env python3
"""Candidates/text2uml-kaiser/run-candidate.py — driver.

Single entry point for all five kaiser strategies
(`kaiser_zero_shot`, `kaiser_one_shot`, `kaiser_few_shot`,
`kaiser_cot`, `kaiser_cot_domain`). Selects the strategy with
``--strategy <name>``, resolves model/sampling parameters, then chains
the three pipeline steps that live in ``Workflow/Benchmark-Workflow/``::

    generate.py   --candidate <strategy-folder>/candidate.py \\
                   --dataset <dataset> --out <results-dir>/<dataset>.json
    score.py      --in <results-dir>/<dataset>.json --metric <metric>
    collect.py    --in <results-dir>/<dataset>_scored.json \\
                   --candidate-id <strategy> \\
                   --candidate-dir <strategy-folder> \\
                   --dataset <dataset> --metric <metric> \\
                   --settings-json '{...}' \\
                   --out-dir <out-dir> --run-index <N>

Output folder (defaults, when neither flag is set)::

    --results-dir : Workflow/Results/cache/
    --out-dir     : Workflow/Results/runs/

The final artifact is a single timestamped JSON per run, named::

    <candidate-id>[_<model-sanitized>]_<utc>.json

with ``<utc>`` of the form ``2026-07-02T14-32-11Z``. The ``--name SUFFIX``
flag inserts an additional token before the timestamp for ad-hoc
disambiguation (e.g. ``--name seed42``).

Usage::

    # Smoke test: zero-shot, 3 records, default model.
    PYTHONPATH=. python Candidates/text2uml-kaiser/run-candidate.py \\
        --strategy kaiser_zero_shot --dataset kaiser_clean --limit 3

    # Full kaiser_clean, deterministic settings, default model.
    PYTHONPATH=. python Candidates/text2uml-kaiser/run-candidate.py \\
        --strategy kaiser_cot --dataset kaiser_clean \\
        --temperature 0.0 --temperature-translate 0.0 --seed 42

    # Override model + temperature.
    PYTHONPATH=. python Candidates/text2uml-kaiser/run-candidate.py \\
        --strategy kaiser_one_shot --dataset kaiser_clean \\
        --model glm-5.1:cloud --temperature 0.7

    # Re-run only the visualiser.
    PYTHONPATH=. python Candidates/text2uml-kaiser/run-candidate.py \\
        --strategy kaiser_few_shot --dataset kaiser_clean \\
        --skip-generate --skip-score

    # Use a custom output folder (bypasses the auto-named default).
    PYTHONPATH=. python Candidates/text2uml-kaiser/run-candidate.py \\
        --strategy kaiser_cot --dataset kaiser_clean \\
        --results-dir /tmp/my-experiment

Model + sampling resolution order (per flag):
      1. CLI flag value.
      2. OLLAMA_MODEL env var (model only).
      3. <strategy-folder>/config.json key.
      4. Project default baked into candidate.py.

Metric resolution order:
      1. --metric on the CLI.
      2. <strategy-folder>/metric.json ({"default_metric": "metrik-1"}).
      3. Project default: metrik-4.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Strategy lookup table.
# ---------------------------------------------------------------------------

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
WORKFLOW_PKG = REPO_ROOT / "Workflow" / "Benchmark-Workflow"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import domain_model_metrics  # noqa: F401

from Metric import METRIC_NAMES


_STRATEGIES: dict[str, dict] = {
    "kaiser_zero_shot": {
        "candidate_path": "zero_shot",
        "skip_folders": [],
    },
    "kaiser_one_shot": {
        "candidate_path": "one_shot",
        "skip_folders": ["AlphaInsurance"],
    },
    "kaiser_few_shot": {
        "candidate_path": "few_shot",
        "skip_folders": ["AlphaInsurance", "GasStation_KUL", "GasStation_TUW"],
    },
    "kaiser_cot": {
        "candidate_path": "cot",
        "skip_folders": [],
    },
    "kaiser_cot_domain": {
        "candidate_path": "cot_domain",
        "skip_folders": [],
    },
}


DEFAULT_METRIC = "metrik-4"
DEFAULT_MODEL = "qwen2.5-coder:7b"


# ---------------------------------------------------------------------------
# Logging.
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Candidates.text2uml_kaiser.run_candidate")


# ---------------------------------------------------------------------------
# Step / config loaders.
# ---------------------------------------------------------------------------

def _load_step(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_strategy_config(strategy_dir: Path) -> dict:
    cfg_path = strategy_dir / "config.json"
    if not cfg_path.is_file():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("could not read %s: %s", cfg_path, exc)
        return {}


def _load_strategy_metric(strategy_dir: Path) -> Optional[str]:
    metric_file = strategy_dir / "metric.json"
    if not metric_file.is_file():
        return None
    try:
        cfg = json.loads(metric_file.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("could not read %s: %s", metric_file, exc)
        return None
    m = cfg.get("default_metric")
    if m and m not in METRIC_NAMES:
        raise SystemExit(
            f"{metric_file} declares default_metric={m!r} "
            f"which is not in {METRIC_NAMES}"
        )
    return m


# ---------------------------------------------------------------------------
# Resolution helpers.
# ---------------------------------------------------------------------------

def _resolve_metric(cli_metric: Optional[str], strategy_dir: Path) -> tuple[str, str]:
    if cli_metric:
        return cli_metric, "cli"
    m = _load_strategy_metric(strategy_dir)
    if m:
        return m, "candidate_metric.json"
    return DEFAULT_METRIC, "project_default"


def _resolve_model(cli_model: Optional[str], cfg: dict) -> tuple[str, str]:
    if cli_model:
        return cli_model, "cli"
    env = os.environ.get("OLLAMA_MODEL")
    if env:
        return env, "env:OLLAMA_MODEL"
    m = cfg.get("default_model")
    if m:
        return m, "config.json::default_model"
    return DEFAULT_MODEL, "project_default"


def _resolve_sampling(
    cli_value, cfg_key: str, cfg: dict, default,
):
    if cli_value is not None:
        return cli_value, "cli"
    v = cfg.get(cfg_key)
    if v is not None:
        return v, f"config.json::{cfg_key}"
    return default, "project_default"


# ---------------------------------------------------------------------------
# Argument parser.
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strategy", required=True, choices=list(_STRATEGIES),
                   help="Which kaiser strategy to run. See the docstring for "
                        "the full list.")
    p.add_argument("--dataset", required=True,
                   choices=["kaiser_clean", "reference_clean",
                            "data-source-1", "data-source-2"],
                   help="Dataset name (or data-source-N alias).")
    p.add_argument("--results-dir", default=None,
                    help="Directory for the intermediate cache JSONs. "
                         "Default: Workflow/Results/cache/.")
    p.add_argument("--out-dir", default=None,
                    help="Directory for the final timestamped run JSON. "
                         "Default: Workflow/Results/runs/.")
    p.add_argument("--limit", type=int, default=None,
                    help="Run only the first N records.")
    p.add_argument("--metric", default=None, choices=METRIC_NAMES,
                    help="Metric to score with. Default: read from "
                         "<strategy-folder>/metric.json, else metrik-4.")
    p.add_argument("--run-index", type=int, default=1,
                    help="1-based run index for repeated runs of the "
                         "same (strategy, model, dataset, settings). "
                         "Encoded in the output filename.")
    p.add_argument("--skip-generate", action="store_true")
    p.add_argument("--skip-score", action="store_true")
    p.add_argument("--skip-collect", action="store_true")
    p.add_argument("--skip-visualise", action="store_true",
                    dest="skip_collect",
                    help=argparse.SUPPRESS)
    p.add_argument("--keep-cache", action="store_true",
                    help="Keep the intermediate cache JSONs (raw + scored) "
                         "in --results-dir after the run completes. "
                         "Default: cache is removed.")

    p.add_argument("--model", default=None,
                   help="Ollama model tag (e.g. qwen2.5-coder:7b, glm-5.1:cloud). "
                        "Overrides OLLAMA_MODEL env var and config.json::default_model.")
    p.add_argument("--temperature", type=float, default=None,
                   help="LLM sampling temperature. Default: config.json::default_temperature (0.7).")
    p.add_argument("--num-predict", type=int, default=None,
                   help="Max output tokens per LLM call. Default: config.json::default_num_predict (1024).")
    p.add_argument("--seed", type=int, default=None,
                   help="Ollama seed for reproducible outputs. Default: config.json::default_seed (null).")
    p.add_argument("--top-p", type=float, default=None,
                   help="Ollama top_p. Default: null (server default).")
    p.add_argument("--top-k", type=int, default=None,
                   help="Ollama top_k. Default: null (server default).")
    p.add_argument("--repeat-penalty", type=float, default=None,
                   help="Ollama repeat_penalty. Default: null (server default).")
    p.add_argument("--timeout", type=int, default=None,
                   help="Per-call Ollama timeout in seconds. Default: config.json::timeout_seconds (600).")
    p.add_argument("--name", default=None,
                    help="Optional disambiguation token inserted into "
                         "the output filename before the timestamp "
                         "(e.g. --name seed42).")
    return p


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)

    strategy = _STRATEGIES[args.strategy]
    candidate_id = args.strategy
    strategy_dir = THIS_DIR / strategy["candidate_path"]
    candidate_path = strategy_dir / "candidate.py"
    if not candidate_path.is_file():
        log.error("candidate.py not found at %s", candidate_path)
        return 1

    cfg = _load_strategy_config(strategy_dir)

    metric, metric_source = _resolve_metric(args.metric, strategy_dir)
    model, model_source = _resolve_model(args.model, cfg)
    temperature, temperature_source = _resolve_sampling(
        args.temperature, "default_temperature", cfg, 0.7)
    num_predict, num_predict_source = _resolve_sampling(
        args.num_predict, "default_num_predict", cfg, 1024)
    seed, seed_source = _resolve_sampling(
        args.seed, "default_seed", cfg, None)
    top_p, top_p_source = _resolve_sampling(
        args.top_p, "default_top_p", cfg, None)
    top_k, top_k_source = _resolve_sampling(
        args.top_k, "default_top_k", cfg, None)
    repeat_penalty, repeat_penalty_source = _resolve_sampling(
        args.repeat_penalty, "default_repeat_penalty", cfg, None)
    timeout, timeout_source = _resolve_sampling(
        args.timeout, "timeout_seconds", cfg, 600)

    results_dir = (
        Path(args.results_dir).resolve() if args.results_dir
        else REPO_ROOT / "Workflow" / "Results" / "cache"
    )
    out_dir = (
        Path(args.out_dir).resolve() if args.out_dir
        else REPO_ROOT / "Workflow" / "Results" / "runs"
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_json = results_dir / f"{args.dataset}.json"
    scored_json = results_dir / f"{args.dataset}_scored.json"

    print("=" * 72)
    print(f"Automated DomainModel Benchmark — driver for {candidate_id}")
    print("=" * 72)
    print(f"  Strategy     : {args.strategy}")
    print(f"  Candidate    : {candidate_path}")
    print(f"  Skip folders : {strategy['skip_folders']}")
    print(f"  Dataset      : {args.dataset}")
    print(f"  Metric       : {metric}  (source: {metric_source})")
    print(f"  Model        : {model}  (source: {model_source})")
    print(f"  Temperature  : {temperature}  (source: {temperature_source})")
    print(f"  Num predict  : {num_predict}  (source: {num_predict_source})")
    print(f"  Seed         : {seed}  (source: {seed_source})")
    print(f"  Top-p        : {top_p}  (source: {top_p_source})")
    print(f"  Top-k        : {top_k}  (source: {top_k_source})")
    print(f"  Repeat penalty: {repeat_penalty}  (source: {repeat_penalty_source})")
    print(f"  Timeout      : {timeout}  (source: {timeout_source})")
    print(f"  Run index    : {args.run_index}")
    print(f"  Results dir  : {results_dir}")
    print(f"  Output dir   : {out_dir}")
    if args.limit:
        print(f"  Limit        : first {args.limit} records")
    print(f"  Steps        : "
          f"{'generate ' if not args.skip_generate else '(skip)generate '}"
          f"{'score ' if not args.skip_score else '(skip)score '}"
          f"{'collect' if not args.skip_collect else '(skip)collect'}")
    print("=" * 72)

    import importlib
    spec = importlib.util.spec_from_file_location(
        f"_cand_{strategy['candidate_path']}", str(candidate_path)
    )
    cand_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cand_mod)
    cand_mod.candidate.__init__(
        model=model,
        temperature=temperature,
        num_predict=num_predict,
        seed=seed,
        top_p=top_p,
        top_k=top_k,
        repeat_penalty=repeat_penalty,
        timeout=timeout,
    )
    log.info("re-instantiated candidate with resolved parameters")

    generate = _load_step("_wf_generate", WORKFLOW_PKG / "generate.py")
    score    = _load_step("_wf_score",    WORKFLOW_PKG / "score.py")
    collect  = _load_step("_wf_collect",  WORKFLOW_PKG / "collect.py")

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

    if not args.skip_collect:
        if not scored_json.exists():
            log.error("collect: input %s missing; run score first", scored_json)
            return 1
        settings = {
            "uses_llm":             True,
            "model":                model,
            "temperature":          temperature,
            "temperature_translate": None,
            "num_predict":          num_predict,
            "seed":                 seed,
            "top_p":                top_p,
            "top_k":                top_k,
            "repeat_penalty":       repeat_penalty,
            "timeout_seconds":      timeout,
            "enable_translation":   None,
            "limit":                args.limit,
        }
        collect_args = [
            "--in",            str(scored_json),
            "--candidate-id",  candidate_id,
            "--candidate-dir", str(strategy_dir),
            "--dataset",       args.dataset,
            "--metric",        metric,
            "--run-index",     str(args.run_index),
            "--settings-json", json.dumps(settings),
            "--out-dir",       str(out_dir),
        ]
        if args.name:
            collect_args.insert(
                collect_args.index("--run-index") + 2,
                "--name",
            )
            collect_args.insert(
                collect_args.index("--name") + 1,
                args.name,
            )
        t0 = time.time()
        rc = collect.main(collect_args)
        print(f"\n[collect]   done in {time.time()-t0:.1f}s (rc={rc}) → {out_dir}")
        if rc != 0:
            return rc
        if not args.keep_cache:
            try:
                shutil.rmtree(results_dir)
                log.info("cleared cache: %s", results_dir)
            except FileNotFoundError:
                pass
            except OSError as exc:
                log.warning("could not clear cache %s: %s", results_dir, exc)

    print(f"\n[run] DONE in {time.time()-t_total:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
