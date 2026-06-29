"""Metric wrapper — thin re-export of `Metric.wrapper`."""
from .wrapper import (
    compute,
    score_one_pair,
    summarise,
    bucketise,
    BUCKETS,
    BUCKET_LABELS,
    METRIC_NAME,
    METRIC_NAMES,
)

__all__ = [
    "compute", "score_one_pair", "summarise", "bucketise",
    "BUCKETS", "BUCKET_LABELS", "METRIC_NAME", "METRIC_NAMES",
]