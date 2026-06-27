"""Workflow — runs every (source/strategy × model × dataset) cell.

Iteration order:
    for spec in registry.all_specs():                 # 11 candidates
        for model in Workflow.config:                 # 4 models
            if not spec.uses_llm: skip model iteration
            for dataset in Workflow.config.datasets:  # 2 datasets
                for record in dataset:                # 45 / 8 records
                    run strategy against record.

Output per cell (one JSON per (source/strategy/model) per dataset):
    Workflow/Results/<source>/<strategy>__<model>/<dataset>.json
        records: [{strategy, source, model, dataset, id, nlt,
                    reference_model, generated_model, failed, error, ...}]

Failure handling:
    Every record runs inside a try/except that converts any error
    into {failed: True, error: "...", generated_model: ""}. The cell
    run never aborts the batch.

CLI:
    PYTHONPATH=. python scripts/run_orchestrator.py
    PYTHONPATH=. python scripts/run_orchestrator.py --smoke
    PYTHONPATH=. python scripts/run_orchestrator.py --strategies text2uml-kaiser
    PYTHONPATH=. python scripts/run_orchestrator.py --models glm kimi
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from Candidates.registry import CandidateSpec, all_specs, get_strategy
from Data import load_dataset
# config_loader is loaded by importlib at runtime to avoid the Workflow
# package shadow issue (see Workflow/README.md).
import importlib.util
_CFG_PATH = Path(__file__).resolve().parent / "config_loader.py"
_cfg_spec = importlib.util.spec_from_file_location("_wf_cfg_loader", _CFG_PATH)
_cfg_mod = importlib.util.module_from_spec(_cfg_spec)
sys.modules["_wf_cfg_loader"] = _cfg_mod
_cfg_spec.loader.exec_module(_cfg_mod)
cfg = _cfg_mod

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.orchestrator")

THIS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = THIS_DIR / "Results"


def _cell_dir(source: str, strategy: str, model: str | None) -> Path:
    """Per-cell output directory: Results/<source>/<strategy>[__<model>]."""
    folder = strategy if model is None else f"{strategy}__{model}"
    return RESULTS_DIR / source / folder


def _cell_path(source: str, strategy: str, model: str | None, dataset: str) -> Path:
    return _cell_dir(source, strategy, model) / f"{dataset}.json"


def _filter_records(rows: list[dict], skip: tuple[str, ...]) -> list[dict]:
    if not skip:
        return rows
    skip_set = set(skip)
    return [r for r in rows if r["id"] not in skip_set]


def _run_one_cell(
    spec: CandidateSpec,
    model: str | None,
    dataset_name: str,
    rows: list[dict],
    *,
    limit: int | None = None,
) -> Path | None:
    """Run a single (source, strategy, model, dataset) cell, write JSON.

    `model` is the **short** name (e.g. `glm`); `model_id` is the full
    Ollama/opencode tag (e.g. `glm-5.1:cloud`). The strategy module
    uses `spec.model` (set to model_id) for the actual LLM call.
    """
    cell_rows = _filter_records(rows, spec.skip_folders)
    if limit is not None:
        cell_rows = cell_rows[:limit]

    model_label = model if model is not None else "-"
    out_path = _cell_path(spec.source, spec.strategy, model, dataset_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    log.info(
        "[%s/%s × %s × %s] %d records (skip %d)",
        spec.source, spec.strategy, model_label, dataset_name,
        len(cell_rows), len(rows) - len(cell_rows),
    )

    # Attach the short model name + the resolved model_id to the spec.
    # The strategy uses `spec.model` for the actual LLM call.
    model_id = ""
    if model is not None:
        m_entry = cfg.model_by_short(model)
        if m_entry is None:
            log.error("unknown model %r; skipping", model)
            return None
        model_id = m_entry["model_id"]
    spec.model = model_id
    spec.model_short = model if model is not None else ""

    records: list[dict] = []
    t0 = time.time()
    for i, row in enumerate(cell_rows, 1):
        rid = row["id"]
        nlt = row["nlt"]
        ref = row["puml"]
        t_run = time.time()
        try:
            result = spec.run_fn(nlt)
        except Exception as exc:
            log.error("strategy %s/%s raised: %s",
                      spec.source, spec.strategy, exc)
            result = {
                "generated_model": "",
                "failed": True,
                "error": f"exception: {type(exc).__name__}: {exc}",
                "raw_excerpt": "",
            }
        elapsed = time.time() - t_run
        records.append({
            "source":          spec.source,
            "strategy":        spec.strategy,
            "model":           model_label,
            "model_id":        spec.model,
            "dataset":         dataset_name,
            "id":              rid,
            "nlt":             nlt,
            "reference_model": ref,
            "generated_model": result.get("generated_model", ""),
            "failed":          bool(result.get("failed", False)),
            "error":           result.get("error"),
            "raw_excerpt":     result.get("raw_excerpt", ""),
            "elapsed_seconds": round(elapsed, 2),
        })
        status = (
            f"  [{i}/{len(cell_rows)}] {rid:30s}  {elapsed:5.1f}s  "
            f"failed={records[-1]['failed']}"
        )
        if records[-1]["error"]:
            status += f"  err={records[-1]['error'][:60]}"
        log.info(status)

    total = time.time() - t0
    payload = {
        "source":         spec.source,
        "strategy":       spec.strategy,
        "model":          model_label,
        "model_id":       spec.model,
        "dataset":        dataset_name,
        "n_total":        len(cell_rows),
        "n_skipped":      len(rows) - len(cell_rows),
        "n_failed":       sum(1 for r in records if r["failed"]),
        "elapsed_seconds":round(total, 2),
        "records":        records,
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info(
        "[%s/%s × %s × %s] wrote %s (%.1fs, %d/%d failed)",
        spec.source, spec.strategy, model_label, dataset_name,
        out_path.relative_to(THIS_DIR), total,
        payload["n_failed"], payload["n_total"],
    )
    return out_path


def _select_specs(source_args: list[str] | None) -> list[CandidateSpec]:
    specs = all_specs()
    if not source_args or "all" in source_args:
        return specs
    return [s for s in specs if s.source in source_args]


def _select_models(model_args: list[str] | None) -> list[str]:
    if not model_args:
        return cfg.model_shorts()
    for m in model_args:
        if cfg.model_by_short(m) is None:
            raise SystemExit(f"unknown model {m!r}; available: {cfg.model_shorts()}")
    return model_args


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strategies", nargs="*", default=None,
        help="Source groups to run (text2uml-kaiser, AutomatedDomainModelling-zenodo, "
             "ai4se_benchmarkPaper, or 'all')",
    )
    ap.add_argument(
        "--models", nargs="*", default=None,
        help="LLM models to run (default: all). Ignored for rule_based.",
    )
    ap.add_argument(
        "--datasets", nargs="*", default=None,
        choices=["kaiser", "reference"],
    )
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--smoke", action="store_true",
        help="Smoke mode: rule_based only, 2 records per dataset.",
    )
    args = ap.parse_args(argv)

    if args.smoke:
        args.strategies = ["ai4se_benchmarkPaper"]
        args.models = []
        args.limit = 2

    specs = _select_specs(args.strategies)
    models = _select_models(args.models)
    datasets = args.datasets or cfg.datasets()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    n_cells = 0
    for spec in specs:
        applicable_models = models if spec.uses_llm else [None]
        for model in applicable_models:
            for ds in datasets:
                rows = load_dataset(ds)
                _run_one_cell(spec, model, ds, rows, limit=args.limit)
                n_cells += 1

    log.info("DONE — %d cells written", n_cells)
    return 0


if __name__ == "__main__":
    sys.exit(main())