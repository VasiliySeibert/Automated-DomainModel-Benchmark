# Workflow/

The benchmark pipeline runs in **three independent steps**, each in its
own Python file, plus a thin driver that chains them.

```
Workflow/
├── generate.py     # Step 1: candidate × dataset → raw JSON
├── score.py        # Step 2: raw JSON → scored JSON
├── visualise.py    # Step 3: scored JSON(s) → bucket tables + heatmaps
├── run_all.py      # Driver: chains the three steps
├── config.json     # (legacy — kept for future model iteration)
├── config_loader.py
├── Notebooks/
│   └── walkthrough.ipynb   # bucket tables, heatmaps, mean bars, errors
└── Results/        # generated, gitignored
```

The whole pipeline is demonstrated below with the
[`Candidates/dummy_candidate/candidate.py`](../Candidates/dummy_candidate/candidate.py)
probe — a deterministic candidate that always emits the same PlantUML
block. Use the dummy to verify the pipeline without LLM latency.

---

## The `Candidate` interface

Every workflow candidate is a Python module exposing a module-level
`candidate` callable:

```python
# Candidate contract:
def candidate(nlt: str) -> CandidateOutput: ...
```

`CandidateOutput` is `{generated_model, failed, error, raw_excerpt}`.
Defined in [`Candidates/candidate_interface.py`](../Candidates/candidate_interface.py).

## The dummy candidate — a worked example

`Candidates/dummy_candidate/candidate.py` is the canonical (and
currently only) implementation. It ignores the NLT entirely and returns
a fixed PUML block:

```python
class DummyCandidate:
    def __call__(self, nlt: str) -> CandidateOutput:
        return CandidateOutput(
            generated_model=_PUML,
            failed=False, error=None,
            raw_excerpt=_PUML[:2000],
        )

candidate = DummyCandidate()
```

Run the full pipeline against it:

```bash
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser
```

This executes all three steps:

```
[generate]  Workflow/Results/dummy_candidate/kaiser_clean.json
[score]     Workflow/Results/dummy_candidate/kaiser_clean_scored.json   (metric: metrik-1)
[visualise] Workflow/Results/_summary.csv
            Workflow/Results/_bucket_kaiser_clean_class_score_metrik-1.csv
            Workflow/Results/_bucket_kaiser_clean_attribute_score_metrik-1.csv
            Workflow/Results/_bucket_kaiser_clean_association_score_metrik-1.csv
            Workflow/Results/_errors.csv
            Workflow/Results/heatmap_kaiser_clean_class_score_metrik-1.png
            Workflow/Results/heatmap_kaiser_clean_attribute_score_metrik-1.png
            Workflow/Results/heatmap_kaiser_clean_association_score_metrik-1.png
```

Because the dummy emits the same PUML regardless of the NLT, every
record scores identically against the kaiser reference set — a useful
sanity check on the metric pipeline. The dummy's `metric.json`
declares `metrik-1` as its default; pass `--metric metrik-4` to
`run_all.py` to override.

---

## Step 1 — `Workflow/generate.py`

Call a candidate against every record in one dataset and write raw
`(nlt, generated, reference)` triples to JSON.

```bash
PYTHONPATH=. python Workflow/generate.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean \
    --limit 3 \
    --out Workflow/Results/dummy_candidate/kaiser_clean.json
```

| Flag | Default | Notes |
|---|---|---|
| `--candidate` | required | path to `candidate.py` or folder containing one |
| `--dataset` | required | `kaiser_clean`, `reference_clean`, or `data-source-N` alias |
| `--out` | required | output JSON path |
| `--limit N` | — | run only the first N records |

Output schema (`<out>.json`):

```json
{
  "candidate":  "Candidates/dummy_candidate/candidate.py",
  "dataset":    "kaiser",
  "clean":      false,
  "n_records":  45,
  "n_failed":   0,
  "elapsed_seconds": 12.3,
  "records": [
    {
      "id":              "AirTravel",
      "nlt":             "...",
      "reference":       "@startuml ... @enduml",
      "generated":       "@startuml ... @enduml",
      "failed":          false,
      "error":           null,
      "raw_excerpt":     "...",
      "elapsed_seconds": 0.04
    }
  ]
}
```

No metric scoring happens here.

## Step 2 — `Workflow/score.py`

Read the JSON from step 1, run metrik on every
`(reference, generated)` pair, append the scores, write
`<stem>_scored.json` next to the input.

```bash
PYTHONPATH=. python Workflow/score.py \
    --in Workflow/Results/dummy_candidate/kaiser_clean.json \
    --metric metrik-1
```

| Flag | Default | Notes |
|---|---|---|
| `--in` | required | input JSON from `generate.py` |
| `--out` | `<stem>_scored.json` | output JSON path |
| `--metric` | `metrik-4` | one of `metrik-1` … `metrik-5` (see below) |

The metric is one of the five metriks exposed by the
[`domain-model-metrics`](https://github.com/VasiliySeibert/domainModel-Metrics-Comparison)
package. All five share the same return-dict shape, so the summariser
works uniformly. Available names: `metrik-1`, `metrik-2`, `metrik-3`,
`metrik-4`, `metrik-5`.

Scored JSON schema — adds `records[i].scores` and a top-level
`summary`:

```json
{
  "records": [
    { ..., "scores": {
        "class_score": 0.12, "attribute_score": 0.0, "association_score": 0.05,
        "parse_warning_ref": [], "parse_warning_gen": [], "error": null
    }}
  ],
  "summary": {
    "class_score":     { "mean": ..., "median": ..., "buckets": [...], ... },
    "attribute_score": { ... },
    "association_score":{ ... }
  },
  "metric_name": "metrik-4"
}
```

## Step 3 — `Workflow/visualise.py`

Read one or more scored JSONs and write cross-candidate aggregations
plus per-(dataset, element) heatmaps.

```bash
PYTHONPATH=. python Workflow/visualise.py \
    --in 'Workflow/Results/*/*_scored.json' \
    --out-dir Workflow/Results \
    --metric metrik-1
```

| Flag | Default | Notes |
|---|---|---|
| `--in` | required (repeatable) | scored JSON path or glob |
| `--out-dir` | required | directory for the aggregation outputs |
| `--metric` | **required** | must match the metric written into every input; bucket tables and heatmaps are suffixed `_<metric>` |

Writes:

```
<out-dir>/_summary.csv                                # long format (metric, candidate, dataset, element, ...)
<out-dir>/_summary.json
<out-dir>/_bucket_<dataset>_<element>_<metric>.csv    # one per (dataset, element)
<out-dir>/_errors.csv                                 # failures
<out-dir>/heatmap_<dataset>_<element>_<metric>.png    # one per (dataset, element)
```

Where `<dataset>` is whichever dataset name was used in step 1
(`kaiser_clean`, `reference_clean`, `data-source-1`, or `data-source-2`).

Mixing scored JSONs that disagree with `--metric` raises a clear error
— re-run `Workflow/score.py --metric <name>` for the offending inputs.

The bucket table schema:

```
candidate,n,n_failed,"[0, 0.1)","[0.1, 0.2)","[0.2, 0.3)","[0.3, 1.0]",mean,median
/Users/.../dummy_candidate/candidate.py,45,0,44,1,0,0,0.04,0.02
```

One row per candidate. Columns are bucket counts plus `n`, `n_failed`,
`mean`, `median`. The same data is shown as a heatmap PNG.

---

## Driver — `Workflow/run_all.py`

Chains the three steps. Each step can be skipped.

### Metric selection

`run_all.py` resolves the metric in this order:

1. `--metric` on the CLI (overrides everything).
2. `<candidate_folder>/metric.json` if it exists, with shape
   `{"default_metric": "metrik-1"}`. The dummy candidate ships one
   declaring `metrik-1`.
3. Project default: `metrik-4`.

The chosen metric is printed in the banner and forwarded to both
`score.py` and `visualise.py`.

### Examples

```bash
# Full pipeline, kaiser_clean only. Uses metrik-1 (from dummy_candidate/metric.json).
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean

# Smaller smoke
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset reference_clean --limit 3

# Override the candidate's metric.json default
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean --metric metrik-4

# Just re-run the visualiser
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean --skip-generate --skip-score

# Use the data-source-N alias
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset data-source-2 --limit 3
```

| Flag | Notes |
|---|---|
| `--candidate` | required (path to `candidate.py` or folder containing one) |
| `--dataset` | required (`kaiser_clean`, `reference_clean`, or `data-source-N` alias) |
| `--metric` | optional; overrides `metric.json` and the default |
| `--results-dir` | default `Workflow/Results/<candidate-name>/` |
| `--out-dir` | default: parent of `--results-dir` |
| `--limit N` | first N records |
| `--skip-generate` / `--skip-score` / `--skip-visualise` | run only the requested steps |

---

## Failure handling

`Workflow/generate.py` catches every exception from the candidate and
records it as `{failed: True, error: "...", generated: ""}`. The run
never aborts mid-dataset.

`Workflow/score.py` reports empty `generated` strings as
`error="empty_generated_model"` with all three scores set to `0.0`.

Failed records appear in `<out-dir>/_errors.csv` with
`{candidate, dataset, id, error, raw_excerpt}` (200-char excerpt of the
candidate's output).

---

## Why no `__init__.py`?

This directory is intentionally NOT a Python package (no `__init__.py`).
The upstream `domain_model_metrics` package injects its
`Quantitative-Analysis/Workflow/` directory onto `sys.path` on import
and then does `from Workflow.metric_interface import ...`. If our local
`Workflow/` folder were a package and got imported first, Python's
import system would cache it under `sys.modules['Workflow']` and the
upstream's `Workflow` would never be resolved.

`Workflow/run_all.py` therefore imports `domain_model_metrics` BEFORE
loading any of the local `Workflow/` files. The step scripts themselves
(`generate.py`, `score.py`, `visualise.py`) are loaded via
`importlib.util.spec_from_file_location` for the same reason.

---

## Notebook

`Workflow/Notebooks/walkthrough.ipynb` consumes the `_summary.csv`,
`_bucket_*.csv`, and `_errors.csv` files produced by step 3 and
renders: bucket tables, per-candidate heatmaps, mean-score bars,
failure-rate bars, and the raw error log. The notebook uses the
`candidate` column (not `strategy`/`model`) throughout.

---

## Migrating the legacy strategies

The 11 pre-existing strategies under `Candidates/text2uml-kaiser/`,
`Candidates/AutomatedDomainModelling_zenodo/`, and
`Candidates/ai4se_benchmarkPaper/rule_based/` still ship their
verbatim prompts, inlined `_ollama.py` HTTP wrappers, and `run()`
functions. They have been stripped of the obsolete `SPEC` /
`register(SPEC)` calls but are **not yet wired** to the new `Candidate`
interface. Migrating each one is a follow-up — wrap its `run` in a
class exposing a `__call__(self, nlt)` method and a module-level
`candidate = MyClass()` instance.