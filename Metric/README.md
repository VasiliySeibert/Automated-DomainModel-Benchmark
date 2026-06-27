# Metric/

The benchmark uses **metrik-4** from the
[`domain-model-metrics`](https://github.com/VasiliySeibert/domainModel-Metrics-Comparison)
package (installed as a dependency). The `wrapper.py` module exposes a single
`compute(ref_puml, gen_puml)` function that:

1. Pre-parses both PlantUML strings with the local `Data.Parser` (strict=False
   so the score is still produced even on partial parse failures).
2. Calls `domain_model_metrics.get_metric("metrik-4").compute(...)`.
3. Returns `{class_score, attribute_score, association_score, parse_warning_ref,
   parse_warning_gen, error}`.

## Why metrik-4

Per the dissertation (`domainModel-Metrics-Comparison` README, §Discussion):

| Element       | RQ1 best (MAD) | RQ2 best (lowest residual std) | RQ2 best (Pearson r) |
|---------------|----------------|--------------------------------|----------------------|
| Class         | metrik-5 (0.07)| metrik-4 (0.07)                | **metrik-4 (0.42)**  |
| Attribute     | **metrik-4 (0.14)** | metrik-3 (0.12)            | metrik-3 (0.65)      |
| Relationship  | metrik-1/3 (0.13) | metrik-4 (0.11)             | **metrik-4 (0.42)**  |

metrik-4 wins 2/3 element×statistic cells and is the recommended single pick
when the practitioner must choose one metric. The other four metrik-1/2/3/5
are available via `compute(..., metric_name="metrik-N")` for ablation.

## Quick start

```python
from Metric import compute, summarise

scores = compute(ref_puml, gen_puml)
print(scores["class_score"], scores["attribute_score"], scores["association_score"])

# Per-dataset summary
summary = summarise([compute(r, g) for r, g in pairs])
print(summary["class_score"]["mean"], summary["class_score"]["buckets"])
```

## FAIR4RS reuse

The metric package is a separate pip-installable artefact with its own
Zenodo DOI. By importing it instead of copying, this benchmark inherits the
upstream's version pinning, citation metadata, and FAIR alignment.

Required citation when publishing benchmark results:

```
Seibert, V. (2026). domain-model-metrics (v1.0.0). Zenodo.
https://doi.org/10.5281/zenodo.20942597
```