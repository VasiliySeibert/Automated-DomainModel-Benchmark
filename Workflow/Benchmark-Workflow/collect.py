#!/usr/bin/env python3
"""Workflow/Benchmark-Workflow/collect.py — step 3 of the benchmark pipeline.

Reads the JSON produced by `Workflow/Benchmark-Workflow/score.py`
(`<stem>_scored.json`), combines it with the resolved candidate
settings supplied by the driver, and writes a single self-describing
run-level JSON that downstream comparison tools consume.

No CSV, no PNG. The output is the canonical artifact for this run.

Usage:
    PYTHONPATH=. python Workflow/Benchmark-Workflow/collect.py \\
        --in Workflow/Results/cache/rule_based/kaiser_clean_scored.json \\
        --candidate-id rule_based \\
        --candidate-dir Candidates/rule_based \\
        --dataset kaiser_clean \\
        --metric metrik-1 \\
        --settings-json '{"uses_llm": false}' \\
        --out-dir Workflow/Results/runs \\
        --run-index 1

Output JSON schema:
    {
      "run_id":         "<utc-timestamp>",
      "timestamp_utc":  "ISO-8601 string",
      "candidate":      "rule_based",            # logical id
      "candidate_path": "Candidates/rule_based", # on-disk location
      "candidate_file": "Candidates/rule_based/candidate.py",
      "dataset":        "kaiser_clean",
      "run_index":      1,
      "metric": {
        "name":            "metrik-1",         # from domain_model_metrics.get_metric(name).name
        "version":         "1.0.0",            # from get_metric(name).version
        "package":         "domain-model-metrics",  # PyPI name
        "package_url":     "https://github.com/VasiliySeibert/domain-model-metrics",
        "package_version": "1.0.0"             # domain_model_metrics.__version__
      },
      "settings": {
        "uses_llm":             bool,
        "model":                str | null,
        "temperature":          float | null,
        "temperature_translate": float | null,
        "num_predict":          int | null,
        "seed":                 int | null,
        "top_p":                float | null,
        "top_k":                int | null,
        "repeat_penalty":       float | null,
        "timeout_seconds":      int | null,
        "enable_translation":   bool | null,
        "limit":                int | null
      },
      "totals": {
        "n_records":               int,
        "n_failed_generate":       int,
        "n_failed_score":          int,
        "elapsed_seconds_generate": float
      },
      "summary": {
        "class_score":       { mean, std, median, mad, n, buckets, failed },
        "attribute_score":   { ... },
        "association_score": { ... }
      },
      "records": [
        {
          "id":              "AirTravel",
          "nlt":             "...",
          "reference":       "@startuml ... @enduml",
          "generated":       "@startuml ... @enduml",
          "failed_generate": bool,
          "error_generate":  str | null,
          "elapsed_seconds": float,
          "scores": {
            "class_score":       float,
            "attribute_score":   float,
            "association_score": float,
            "parse_warning_ref": list[str],
            "parse_warning_gen": list[str],
            "error":             str | null
          },
          "buckets": {
            "class_score":       "<bucket-label>",
            "attribute_score":   "<bucket-label>",
            "association_score": "<bucket-label>"
          }
        },
        ...
      ]
    }

Output filename pattern:
    <out-dir>/<candidate-id>[_<model-sanitized>]_<utc-timestamp>.json

`<dataset>` and `<run_index>` are intentionally NOT in the filename —
they live in the JSON body. The timestamp is the unique-per-invocation
discriminator; `<model-sanitized>` (when set) makes the file sortable
when the same candidate is run against multiple LLMs.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import domain_model_metrics

from Metric import BUCKET_LABELS, bucketise


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.collect")


ELEMENTS = ("class_score", "attribute_score", "association_score")

_PYPI_PACKAGE = "domain-model-metrics"
_PACKAGE_URL = "https://github.com/VasiliySeibert/domain-model-metrics"

_INVALID_PATH_CHARS = re.compile(r"[^\w.-]")


def _sanitize_model_for_path(model: str | None) -> str | None:
    """Sanitise an Ollama model tag for use as a filename component.

    Returns None for None; otherwise replaces any character outside
    ``[A-Za-z0-9_.-]`` with an underscore and strips the result.
    """
    if model is None:
        return None
    s = _INVALID_PATH_CHARS.sub("_", str(model)).strip("_")
    return s or None


def _utc_timestamp(seconds: bool = True) -> str:
    """Return the current UTC time. With ``seconds=True`` the format is
    ``YYYY-MM-DDTHH-MM-SSZ`` (filesystem-safe). The companion ISO string
    lives in the JSON body for machine readability.
    """
    fmt = "%Y-%m-%dT%H-%M-%SZ" if seconds else "%Y-%m-%dT%H-%M-%S"
    return datetime.now(timezone.utc).strftime(fmt)


def _iso_utc_now() -> str:
    """Return current UTC time as ISO 8601 with explicit timezone."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _bucket_label(score) -> str | None:
    if score is None:
        return None
    idx = bucketise(float(score))
    if idx is None or not (0 <= idx < len(BUCKET_LABELS)):
        return None
    return BUCKET_LABELS[idx]


def _resolve_metric_identity(metric_name: str) -> dict:
    """Resolve the metric's identity from the dependency package.

    Returns a dict with the metric's own name + version (per
    ``domain_model_metrics.get_metric(name)``) plus the PyPI package
    name + version (per ``domain_model_metrics.__version__``).
    """
    try:
        m = domain_model_metrics.get_metric(metric_name)
        m_name = getattr(m, "name", metric_name)
        m_version = getattr(m, "version", None)
    except Exception as exc:
        log.warning("could not resolve metric %r from domain_model_metrics: %s",
                    metric_name, exc)
        m_name = metric_name
        m_version = None
    return {
        "name":            m_name,
        "version":         m_version,
        "package":         _PYPI_PACKAGE,
        "package_url":     _PACKAGE_URL,
        "package_version": getattr(domain_model_metrics, "__version__", None),
    }


def _build_records(scored_payload: dict) -> list[dict]:
    out: list[dict] = []
    for r in scored_payload.get("records", []):
        scores = r.get("scores") or {}
        out.append({
            "id":              r.get("id", ""),
            "nlt":             r.get("nlt", ""),
            "reference":       r.get("reference", ""),
            "generated":       r.get("generated", ""),
            "failed_generate": bool(r.get("failed", False)),
            "error_generate":  r.get("error"),
            "elapsed_seconds": r.get("elapsed_seconds"),
            "scores": {
                "class_score":       scores.get("class_score"),
                "attribute_score":   scores.get("attribute_score"),
                "association_score": scores.get("association_score"),
                "parse_warning_ref": scores.get("parse_warning_ref", []),
                "parse_warning_gen": scores.get("parse_warning_gen", []),
                "error":             scores.get("error"),
            },
            "buckets": {
                "class_score":       _bucket_label(scores.get("class_score")),
                "attribute_score":   _bucket_label(scores.get("attribute_score")),
                "association_score": _bucket_label(scores.get("association_score")),
            },
        })
    return out


def _settings_with_defaults(settings: dict, limit: int | None) -> dict:
    """Return a normalised settings dict with stable keys.

    Missing keys become None so downstream consumers can rely on the
    full schema even for non-LLM candidates.
    """
    return {
        "uses_llm":             settings.get("uses_llm", False),
        "model":                settings.get("model"),
        "temperature":          settings.get("temperature"),
        "temperature_translate": settings.get("temperature_translate"),
        "num_predict":          settings.get("num_predict"),
        "seed":                 settings.get("seed"),
        "top_p":                settings.get("top_p"),
        "top_k":                settings.get("top_k"),
        "repeat_penalty":       settings.get("repeat_penalty"),
        "timeout_seconds":      settings.get("timeout_seconds"),
        "enable_translation":   settings.get("enable_translation"),
        "limit":                limit,
    }


def _build_filename(
    candidate_id: str,
    model: str | None,
    timestamp: str,
    name: str | None = None,
) -> str:
    parts = [candidate_id]
    sm = _sanitize_model_for_path(model)
    if sm:
        parts.append(sm)
    if name:
        parts.append(_sanitize_model_for_path(name) or "x")
    parts.append(timestamp)
    return "_".join(parts) + ".json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", required=True,
                    help="Path to <dataset>_scored.json (from score.py).")
    ap.add_argument("--candidate-id", required=True,
                    help="Logical candidate identifier (e.g. 'rule_based', "
                         "'zenodo_zero_shot').")
    ap.add_argument("--candidate-dir", required=True,
                    help="Path to the candidate folder (used for "
                         "candidate_path in the output).")
    ap.add_argument("--candidate-path", default=None,
                    help="Optional explicit path to candidate.py. Default: "
                         "<candidate-dir>/candidate.py")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--metric", required=True)
    ap.add_argument("--run-index", type=int, default=1,
                    help="1-based run index for repeated runs of the "
                         "same (candidate, model, dataset, settings).")
    ap.add_argument("--name", default=None,
                    help="Optional disambiguation token inserted into "
                         "the filename before the timestamp (e.g. 'seed42').")
    ap.add_argument("--settings-json", default="{}",
                    help="JSON object string of resolved settings "
                         "(model, temperature, etc.). Default: {}.")
    ap.add_argument("--out-dir", required=True,
                    help="Directory to write the timestamped JSON into.")
    args = ap.parse_args(argv)

    in_path = Path(args.in_path).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("collecting %s → %s", in_path, out_dir)

    scored = json.loads(in_path.read_text(encoding="utf-8"))
    if scored.get("metric_name") and scored["metric_name"] != args.metric:
        log.warning(
            "input %s was scored with %s but --metric=%s; using --metric "
            "as the authoritative value in the run JSON",
            in_path, scored.get("metric_name"), args.metric,
        )

    try:
        settings_raw = json.loads(args.settings_json) if args.settings_json else {}
    except json.JSONDecodeError as exc:
        log.error("--settings-json is not valid JSON: %s", exc)
        return 1
    if not isinstance(settings_raw, dict):
        log.error("--settings-json must decode to an object, got %s",
                  type(settings_raw).__name__)
        return 1

    timestamp = _utc_timestamp()
    filename = _build_filename(
        candidate_id=args.candidate_id,
        model=settings_raw.get("model"),
        timestamp=timestamp,
        name=args.name,
    )
    out_path = out_dir / filename

    candidate_path = (
        args.candidate_path if args.candidate_path
        else str(Path(args.candidate_dir).resolve() / "candidate.py")
    )

    records = _build_records(scored)
    n_records = len(records)
    n_failed_generate = sum(1 for r in records if r["failed_generate"])
    n_failed_score = sum(
        1 for r in records
        if r["scores"].get("error") and not r["failed_generate"]
    )
    elapsed_generate = scored.get("elapsed_seconds")

    summary = scored.get("summary") or {}
    payload = {
        "run_id":         timestamp,
        "timestamp_utc":  _iso_utc_now(),
        "candidate":      args.candidate_id,
        "candidate_path": str(Path(args.candidate_dir).resolve()),
        "candidate_file": candidate_path,
        "dataset":        args.dataset,
        "run_index":      args.run_index,
        "metric":         _resolve_metric_identity(args.metric),
        "settings":       _settings_with_defaults(settings_raw, scored.get("__limit")),
        "totals": {
            "n_records":               n_records,
            "n_failed_generate":       n_failed_generate,
            "n_failed_score":          n_failed_score,
            "elapsed_seconds_generate": elapsed_generate,
        },
        "summary":  summary,
        "records":  records,
    }

    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    log.info("wrote %s (n=%d, failed_gen=%d, failed_score=%d)",
             out_path, n_records, n_failed_generate, n_failed_score)
    print(f"\n[collect]   done → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
