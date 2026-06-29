"""Thin wrapper around `domain-model-metrics` (the FAIR4RS dependency).

The wrapper exposes one public function, `compute(ref_puml, gen_puml)`,
that runs the PlantUML parser first (to capture warnings) and then defers
to `metrik-4`. metrik-4 is the recommended per-element pick from the
`domainModel-Metrics-Comparison` study — highest Pearson r on Class (0.42)
and Relationship (0.42), lowest MAD on Attribute (0.14).

The wrapper also provides:
- `BUCKETS`     — score bucket boundaries used for the result tables
- `bucketise()` — convert a score to its bucket index
- `summarise()` — per-element mean / std / median / bucket counts

Bucket rationale (see Workflow/Benchmark-Workflow/README.md):
    Ten per-decile buckets `[0, 0.1)` through `[0.9, 1.0]` give
    finer resolution across the full 0-1 score range, including the
    typical good-score cluster around ~0.7 (the projection of the
    identical-input ceiling onto the human F1 scale for several
    metriks). The earlier four-bucket layout collapsed most of the
    upper half into a single bucket and was too coarse to
    discriminate between decent and genuinely good candidates.
"""
from __future__ import annotations

import importlib
import logging
from functools import lru_cache

log = logging.getLogger(__name__)

METRIC_NAME = "metrik-4"

# The five metriks exposed by the upstream `domain-model-metrics` package.
# All five share the same return-dict shape (class_score, attribute_score,
# association_score, parse_warning_ref/gen, error), so summarise() works
# uniformly across them.
METRIC_NAMES: tuple[str, ...] = (
    "metrik-1", "metrik-2", "metrik-3", "metrik-4", "metrik-5",
)

# Bucket boundaries — left-closed, right-open except the last.
BUCKETS: tuple[float, ...] = (
    0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001,
)
BUCKET_LABELS: tuple[str, ...] = (
    "[0, 0.1)",    "[0.1, 0.2)", "[0.2, 0.3)", "[0.3, 0.4)",
    "[0.4, 0.5)",  "[0.5, 0.6)", "[0.6, 0.7)", "[0.7, 0.8)",
    "[0.8, 0.9)",  "[0.9, 1.0]",
)


@lru_cache(maxsize=1)
def _get_metric():
    """Lazy-load the canonical metrik-4 orchestrator (one import per process)."""
    factory = importlib.import_module("domain_model_metrics")
    return factory.get_metric(METRIC_NAME)


def _load_parser():
    from Data.Parser import PlantUMLParser
    return PlantUMLParser(strict=False)


def _pre_parse(puml: str, parser) -> tuple[str | None, list[str]]:
    try:
        model = parser.parse(puml)
        warnings = list(getattr(parser, "warnings", []) or [])
        if getattr(model, "warnings", None):
            warnings.extend(model.warnings)
        return None, warnings
    except Exception as exc:
        return str(exc), []


def compute(ref_puml: str, gen_puml: str, *, metric_name: str = METRIC_NAME) -> dict:
    """Compute per-element similarity. Short-circuits on empty generated input."""
    if not gen_puml or not gen_puml.strip():
        return {
            "class_score": 0.0,
            "attribute_score": 0.0,
            "association_score": 0.0,
            "parse_warning_ref": [],
            "parse_warning_gen": [],
            "error": "empty_generated_model",
        }

    parser = _load_parser()
    err_ref, warn_ref = _pre_parse(ref_puml, parser)
    err_gen, warn_gen = _pre_parse(gen_puml, parser)

    error = err_ref or err_gen
    if error:
        log.warning("PlantUML parse failure: %s", error)

    metric = (
        _get_metric()
        if metric_name == METRIC_NAME
        else importlib.import_module("domain_model_metrics").get_metric(metric_name)
    )
    raw = metric.compute(ref_puml, gen_puml)
    return {
        "class_score": raw["class_score"],
        "attribute_score": raw["attribute_score"],
        "association_score": raw["association_score"],
        "parse_warning_ref": warn_ref,
        "parse_warning_gen": warn_gen,
        "error": error,
    }


def bucketise(score: float | None) -> int | None:
    """Return the bucket index for `score`, or None if score is None.

    Valid indices are 0 .. len(BUCKETS)-2 inclusive (one bucket per
    adjacent pair of boundaries).
    """
    if score is None:
        return None
    for i, upper in enumerate(BUCKETS[1:]):
        if score < upper:
            return i
    return len(BUCKETS) - 2


def summarise(scores: list[dict]) -> dict:
    """Aggregate per-element statistics over a list of per-pair score dicts."""
    import statistics as st

    out: dict[str, dict] = {}
    for element in ("class_score", "attribute_score", "association_score"):
        vals = [s[element] for s in scores if s.get(element) is not None]
        if not vals:
            out[element] = {
                "mean": None, "std": None, "median": None,
                "mad": None, "n": 0,
                "buckets": [0] * (len(BUCKETS) - 1),
                "failed": sum(1 for s in scores if s.get("error")),
            }
            continue
        mean = st.fmean(vals)
        std = st.pstdev(vals) if len(vals) > 1 else 0.0
        med = st.median(vals)
        mad = st.fmean([abs(v - mean) for v in vals]) if vals else 0.0
        buckets = [0] * (len(BUCKETS) - 1)
        for v in vals:
            idx = bucketise(v)
            if idx is not None:
                buckets[idx] += 1
        failed = sum(1 for s in scores if s.get("error"))
        out[element] = {
            "mean": mean, "std": std, "median": med, "mad": mad,
            "n": len(vals), "buckets": buckets, "failed": failed,
        }
    return out


def score_one_pair(ref_puml: str, gen_puml: str) -> dict:
    """Convenience alias used by the workflow orchestrator."""
    return compute(ref_puml, gen_puml)


__all__ = [
    "compute", "score_one_pair", "summarise", "bucketise",
    "BUCKETS", "BUCKET_LABELS", "METRIC_NAME", "METRIC_NAMES",
]