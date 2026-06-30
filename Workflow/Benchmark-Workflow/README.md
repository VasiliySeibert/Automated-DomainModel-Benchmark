# Workflow/Benchmark-Workflow/

The benchmark pipeline runs in **three independent steps**, each in
its own Python file. The per-group drivers in `Candidates/<group>/`
chain the steps in order, default the paths, and apply the
group-specific sampling flags.

```
Workflow/Benchmark-Workflow/
├── generate.py     # Step 1: candidate × dataset → raw JSON
├── score.py        # Step 2: raw JSON → scored JSON (with metrik-N)
├── visualise.py    # Step 3: scored JSON(s) → bucket tables + heatmaps
├── __init__.py     # Marks this folder as a Python subpackage
├── config.json     # Legacy model registry, kept for future iteration
├── config_loader.py
└── README.md       # This file
```

The surrounding layout:

```
Workflow/
├── README.md                       # Slim index pointing at this folder
├── Benchmark-Workflow/             # ← pipeline scripts live here
├── Notebooks/
│   └── walkthrough.ipynb           # consumes the output CSVs / heatmaps
└── Results/                        # generated, gitignored
```

You can invoke the step scripts directly to mix-and-match runs, but
the common path is to call a per-group driver. The driver
`Candidates/<group>/run-candidate.py` (or `run.py` for the two
non-LLM candidates) does steps 1, 2, 3 in order.

---

## The `Candidate` interface

Every workflow candidate is a Python module exposing a module-level
`candidate` callable:

```python
# Candidate contract:
def candidate(nlt: str) -> CandidateOutput: ...
```

`CandidateOutput` is a `TypedDict` with these fields:

| Field | Type | Notes |
|---|---|---|
| `generated_model` | `str` | The final PlantUML (post-validator, post-auto-repair). |
| `failed` | `bool` | `True` if the candidate's `__call__` raised. |
| `error` | `Optional[str]` | Error string (see *Failure modes* below). |
| `raw_excerpt` | `str` | First ~2000 chars of the LLM response, for debugging. |

Defined in [`Candidates/candidate_interface.py`](../../Candidates/candidate_interface.py).
The `load_candidate(path)` helper there accepts either a path to
`candidate.py` or a folder containing one, and returns the
module-level `candidate` callable.

The simplest possible candidate — `Candidates/dummy_candidate/candidate.py`:

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

The dummy ignores the NLT entirely and returns a fixed PUML block
— a useful sanity check on the metric pipeline because every
record scores identically against the reference set.

---

## Per-group drivers

The per-group drivers live in `Candidates/<group>/`. They are the
operational surface of the pipeline. Each driver accepts
`--strategy <name>`, `--dataset <name>`, and the LLM sampling
flags (`--temperature`, `--limit`, etc.), then chains steps 1, 2, 3
in order.

| Group | Driver | Strategies | Datasets | Skip folders |
|---|---|---|---|---|
| zenodo | `Candidates/AutomatedDomainModelling_zenodo/run-candidate.py` | `zenodo_zero_shot`, `zenodo_one_shot_btms`, `zenodo_one_shot_h2s_short`, `zenodo_two_shot`, `zenodo_cot` | `kaiser_clean`, `reference_clean` | per-strategy (see [zenodo README](../../Candidates/AutomatedDomainModelling_zenodo/README.md)) |
| kaiser | `Candidates/text2uml-kaiser/run-candidate.py` | `kaiser_zero_shot`, `kaiser_one_shot`, `kaiser_few_shot`, `kaiser_cot`, `kaiser_cot_domain` | `kaiser_clean`, `reference_clean` | per-strategy (see [kaiser README](../../Candidates/text2uml-kaiser/README.md)) |
| rule_based | `Candidates/rule_based/run.py` | `rule_based` (only) | `kaiser_clean`, `reference_clean` | — |
| dummy_candidate | `Candidates/dummy_candidate/run.py` | `dummy_candidate` (only) | `kaiser_clean`, `reference_clean` | — |

Each driver accepts `--strategy <name>` (or operates on its single
strategy directly), `--dataset kaiser_clean | reference_clean |
data-source-N`, `--metric metrik-1…metrik-5` (defaulting to the
candidate's `metric.json`), `--limit N`, and the LLM sampling flags.
See the per-group READMEs for the full flag surface.

The two non-LLM candidates (`rule_based`, `dummy_candidate`) have
their own self-contained `run.py` files because they have no LLM
sampling surface. The 10 LLM-driven strategies share the
`run-candidate.py` pattern.

---

## Step 1 — `Workflow/Benchmark-Workflow/generate.py`

Call a candidate against every record in one dataset and write raw
`(nlt, generated, reference)` triples to JSON.

```bash
PYTHONPATH=. python Workflow/Benchmark-Workflow/generate.py \
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

No metric scoring happens here. Records where the candidate's
`__call__` raised are still in the file, with `failed: True` and
`generated: ""`.

## Step 2 — `Workflow/Benchmark-Workflow/score.py`

Read the JSON from step 1, run the metrik on every
`(reference, generated)` pair, append the scores, and write
`<stem>_scored.json` next to the input.

```bash
PYTHONPATH=. python Workflow/Benchmark-Workflow/score.py \
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
package. All five share the same return-dict shape, so the
summariser works uniformly. Available names: `metrik-1`,
`metrik-2`, `metrik-3`, `metrik-4`, `metrik-5`.

The default `--metric` is `metrik-4` at the project level. Each
candidate's `metric.json` can override it with `default_metric`
(e.g. `Candidates/dummy_candidate/metric.json` declares `metrik-1`).
CLI flag wins over `metric.json` wins over the project default.

Scored JSON schema — adds `records[i].scores` and a top-level
`summary`:

```json
{
  "records": [
    { "...", "scores": {
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

## Step 3 — `Workflow/Benchmark-Workflow/visualise.py`

Read one or more scored JSONs and write cross-candidate
aggregations plus per-(dataset, element) heatmaps.

```bash
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
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
(`kaiser_clean`, `reference_clean`, `data-source-1`, or
`data-source-2`).

Mixing scored JSONs that disagree with `--metric` raises a clear
error — re-run `Workflow/Benchmark-Workflow/score.py --metric <name>`
for the offending inputs.

The bucket table schema:

```
candidate,n,n_failed,"[0, 0.1)","[0.1, 0.2)",...,"[0.9, 1.0]",mean,median
/Users/.../dummy_candidate/candidate.py,45,0,37,7,...,0,0.0414,0.0000
```

Ten buckets total — see `Metric/wrapper.py` `BUCKETS` /
`BUCKET_LABELS` for the canonical list. One row per candidate.
Columns are bucket counts plus `n`, `n_failed`, `mean`, `median`.
The same data is shown as a heatmap PNG.

---

## Failure handling

The pipeline is fail-soft: a single bad record never aborts the
run.

**Step 1 (`generate.py`)** catches every exception from the
candidate's `__call__` and records it as
`{failed: True, error: "...", generated: ""}`. The run never
aborts mid-dataset.

**Step 2 (`score.py`)** reports empty `generated` strings as
`error="empty_generated_model"` with all three scores set to `0.0`.
The metrik-4 parser handles partial diagrams gracefully — a record
that produced a valid-but-incomplete PUML still gets non-zero
scores.

**Failed records** appear in `<out-dir>/_errors.csv` with
`{candidate, dataset, id, error, raw_excerpt}` (200-char excerpt of
the candidate's output). The full `generated_model` field (after
auto-repair) is in the scored JSON.

### Error taxonomy

The candidate's `error` string follows a structured taxonomy:

| `error` string | Cause |
|---|---|
| `exception: <class>: <msg>` | The Ollama call raised (e.g. `ConnectionError`). |
| `*_no_plantuml` | The LLM response had no `@startuml…@enduml` block. |
| `*_no_classes` / `*_step*_no_classes` | CoT step 1 or 2 returned no parseable class list. |
| `plantuml_validator: <errors>` | The validator rejected the final PUML. |

The `*` prefix varies by strategy (e.g. `zenodo_cot_no_plantuml`).
The taxonomy is structured for grouping in the analysis notebook
(filtering on the prefix).

### Validator auto-repair

The shared validator at
`Candidates/AutomatedDomainModelling_zenodo/plantuml_validator.py`
auto-repairs mechanical issues:
- Missing `class` keyword before identifier.
- Unquoted cardinalities in associations.
- Referenced-but-undeclared classes (declared with a placeholder).

Non-mechanical issues (unrecognised line kinds, invalid
identifiers) are surfaced as `plantuml_validator: <errors>` and
fail-closed. The repaired PUML is what's returned in
`generated_model` and scored.

---

## Why the outer `Workflow/` is not a package

The outer `Workflow/` directory is intentionally **not** a Python
package (no `__init__.py`). The upstream `domain_model_metrics`
package injects its own `Workflow/` directory onto `sys.path` on
import and then does `from Workflow.metric_interface import ...`.
If our outer `Workflow/` had an `__init__.py` and was imported
first, Python's import system would cache it under
`sys.modules['Workflow']` and the upstream's `Workflow` would never
be resolved.

`Workflow/Benchmark-Workflow/` only registers itself as
`Workflow.Benchmark-Workflow` / `Benchmark-Workflow` in
`sys.modules` — it does not register bare `Workflow`, so the shadow
analysis is preserved.

Each per-group driver (e.g.
`Candidates/AutomatedDomainModelling_zenodo/run-candidate.py`)
imports `domain_model_metrics` before it imports the step scripts
in this folder, for the same reason. The step scripts themselves
are loaded via `importlib.util.spec_from_file_location` to keep
`sys.modules` clean of `Workflow` aliases.

---

## Adding a new strategy

For the operational steps (create the strategy folder, register in
the per-group driver, smoke-test, log in `adjustments.md`), see
the *Adding a new strategy* section in the top-level `README.md`.
The pipeline scripts (`generate.py`, `score.py`, `visualise.py`)
need no edits.

---

## Notebook

`Workflow/Notebooks/walkthrough.ipynb` consumes the `_summary.csv`,
`_bucket_*.csv`, and `_errors.csv` files produced by step 3 and
renders: bucket tables, per-candidate heatmaps, mean-score bars,
failure-rate bars, and the raw error log. The notebook uses the
`candidate` column (not `strategy`/`model`) throughout for
cross-candidate comparisons.

---

## Where to read more

- [`../../README.md`](../../README.md) — the entry point, with the
  full strategy list, dataset descriptions, output folder shape,
  and the LLM sampling parameter resolution order.
- [`../../Candidates/adjustments.md`](../../Candidates/adjustments.md) —
  the migration log, recording every architectural change since
  the rewrite.
- The per-group READMEs in `../../Candidates/<group>/README.md` —
  the operational surface for each group (flags, paths, failure
  modes, per-strategy details).
