#!/usr/bin/env python3
"""Candidates/AutomatedDomainModelling_zenodo/zero_shot/run.py — driver.

Hard-codes the two-stage zero-shot `candidate.py` and chains the three
pipeline steps that live in `Workflow/Benchmark-Workflow/`:

    generate.py   --candidate Candidates/AutomatedDomainModelling_zenodo/zero_shot \\
                   --dataset <dataset> --out <results-dir>/<dataset>.json
    score.py      --in <results-dir>/<dataset>.json --metric <metric>
    visualise.py  --in <results-dir>/<dataset>_scored.json \\
                   --out-dir <out-dir> --metric <metric>

Usage:
    # First, make sure Ollama is running and the model is pulled:
    ollama serve &
    ollama pull qwen2.5-coder:7b

    PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/zero_shot/run.py \\
        --dataset kaiser_clean --limit 3

    # Override the model, temperature, and disable stage-2 translation
    PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/zero_shot/run.py \\
        --dataset kaiser_clean --model minimax-m3:cloud --temperature 0.0 \\
        --no-translate

    # Re-run only the visualiser
    PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/zero_shot/run.py \\
        --dataset kaiser_clean --skip-generate --skip-score

Model + sampling resolution order (per flag):
      1. CLI flag value.
      2. OLLAMA_MODEL env var (model only).
      3. config.json key.
      4. Project default baked into candidate.py.

Metric resolution order (same as the other drivers):
      1. --metric on the CLI.
      2. Candidates/AutomatedDomainModelling_zenodo/zero_shot/metric.json
         ({"default_metric": "metrik-1"}).
      3. Project default: metrik-4.

Output layout (under --results-dir, default Workflow/Results/zenodo_zero_shot/):
    <results-dir>/<dataset>.json         # step 1: raw generate output
    <results-dir>/<dataset>_scored.json  # step 2: scored
    <out-dir>/_summary.csv               # step 3: aggregation table
    <out-dir>/_summary.json              # step 3: aggregation table (json)
    <out-dir>/_bucket_<dataset>_<element>_<metric>.csv
    <out-dir>/_errors.csv                # step 3: failure log
    <out-dir>/heatmap_<dataset>_<element>_<metric>.png
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path


CANDIDATE_ID = "zenodo_zero_shot"
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent.parent            # repo root
WORKFLOW_PKG = REPO_ROOT / "Workflow" / "Benchmark-Workflow"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import domain_model_metrics  # noqa: F401

from Metric import METRIC_NAMES


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Candidates.zenodo_zero_shot.run")


DEFAULT_METRIC = "metrik-4"


def _load_step(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_config() -> dict:
    cfg_path = THIS_DIR / "config.json"
    if not cfg_path.is_file():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("could not read %s: %s", cfg_path, exc)
        return {}


def _resolve_metric(cli_metric: str | None) -> tuple[str, str]:
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


def _resolve_model(cli_model: str | None, cfg: dict) -> str:
    if cli_model:
        return cli_model, "cli"
    env = os.environ.get("OLLAMA_MODEL")
    if env:
        return env, "env:OLLAMA_MODEL"
    m = cfg.get("default_model")
    if m:
        return m, "config.json::default_model"
    return "qwen2.5-coder:7b", "project_default"


def _resolve_sampling(
    cli_value,
    cfg_key: str,
    cfg: dict,
    default,
):
    if cli_value is not None:
        return cli_value, "cli"
    v = cfg.get(cfg_key)
    if v is not None:
        return v, f"config.json::{cfg_key}"
    return default, "project_default"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True,
                    choices=["kaiser_clean", "reference_clean",
                             "data-source-1", "data-source-2"],
                    help="Dataset name (or data-source-N alias).")
    ap.add_argument("--results-dir", default=None,
                    help="Directory for the JSONs and aggregator outputs. "
                         "Default: Workflow/Results/zenodo_zero_shot/")
    ap.add_argument("--out-dir", default=None,
                    help="Directory for visualiser outputs "
                         "(_summary.csv, _bucket_*.csv, _errors.csv, "
                         "heatmap_*.png). Default: same as --results-dir.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Run only the first N records.")
    ap.add_argument("--metric", default=None, choices=METRIC_NAMES,
                    help="Metric to score with. Default: read from "
                         "Candidates/AutomatedDomainModelling_zenodo/zero_shot/metric.json, else metrik-4.")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--skip-score", action="store_true")
    ap.add_argument("--skip-visualise", action="store_true")

    ap.add_argument("--model", default=None,
                    help="Ollama model tag (e.g. qwen2.5-coder:7b, minimax-m3:cloud). "
                         "Overrides OLLAMA_MODEL env var and config.json::default_model.")
    ap.add_argument("--temperature", type=float, default=None,
                    help="Stage 1 (extraction) temperature. Default: config.json::default_temperature (0.7).")
    ap.add_argument("--temperature-translate", type=float, default=None,
                    help="Stage 2 (translation) temperature. Default: config.json::default_temperature_translate (0.0).")
    ap.add_argument("--num-predict", type=int, default=None,
                    help="Max output tokens per LLM call. Default: config.json::default_num_predict (1024).")
    ap.add_argument("--seed", type=int, default=None,
                    help="Ollama seed for reproducible outputs. Default: config.json::default_seed (null).")
    ap.add_argument("--top-p", type=float, default=None,
                    help="Ollama top_p. Default: null (server default).")
    ap.add_argument("--top-k", type=int, default=None,
                    help="Ollama top_k. Default: null (server default).")
    ap.add_argument("--repeat-penalty", type=float, default=None,
                    help="Ollama repeat_penalty. Default: null (server default).")
    ap.add_argument("--timeout", type=int, default=None,
                    help="Per-call Ollama timeout in seconds. Default: config.json::timeout_seconds (600).")
    ap.add_argument("--no-translate", action="store_true",
                    help="Disable stage 2 (translation prompt). A/B comparison mode.")
    args = ap.parse_args(argv)

    candidate_path = THIS_DIR / "candidate.py"
    cfg = _load_config()

    metric, metric_source = _resolve_metric(args.metric)
    model, model_source = _resolve_model(args.model, cfg)
    temperature, temperature_source = _resolve_sampling(
        args.temperature, "default_temperature", cfg, 0.7)
    temperature_translate, temperature_translate_source = _resolve_sampling(
        args.temperature_translate, "default_temperature_translate", cfg, 0.0)
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
    enable_translation = not args.no_translate
    if args.no_translate:
        enable_translation_source = "cli:--no-translate"
    else:
        enable_translation = cfg.get("enable_translation", True)
        enable_translation_source = "config.json::enable_translation"

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
    print(f"  Model        : {model}  (source: {model_source})")
    print(f"  Temperature  : {temperature}  (source: {temperature_source})")
    print(f"  Temp translate: {temperature_translate}  (source: {temperature_translate_source})")
    print(f"  Num predict  : {num_predict}  (source: {num_predict_source})")
    print(f"  Seed         : {seed}  (source: {seed_source})")
    print(f"  Top-p        : {top_p}  (source: {top_p_source})")
    print(f"  Top-k        : {top_k}  (source: {top_k_source})")
    print(f"  Repeat penalty: {repeat_penalty}  (source: {repeat_penalty_source})")
    print(f"  Timeout      : {timeout}  (source: {timeout_source})")
    print(f"  Translation  : {enable_translation}  (source: {enable_translation_source})")
    print(f"  Results dir  : {results_dir}")
    print(f"  Output dir   : {out_dir}")
    if args.limit:
        print(f"  Limit        : first {args.limit} records")
    print(f"  Steps        : "
          f"{'generate ' if not args.skip_generate else '(skip)generate '}"
          f"{'score ' if not args.skip_score else '(skip)score '}"
          f"{'visualise' if not args.skip_visualise else '(skip)visualise'}")
    print("=" * 72)

    import Candidates.AutomatedDomainModelling_zenodo.zero_shot.candidate as cand_mod
    cand_mod.candidate.__init__(
        model=model,
        temperature=temperature,
        temperature_translate=temperature_translate,
        num_predict=num_predict,
        seed=seed,
        top_p=top_p,
        top_k=top_k,
        repeat_penalty=repeat_penalty,
        timeout=timeout,
        enable_translation=enable_translation,
    )
    log.info("re-instantiated candidate with resolved parameters")

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
