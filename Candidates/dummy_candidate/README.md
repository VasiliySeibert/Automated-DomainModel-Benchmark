# dummy_candidate

A **deterministic constant-output** Candidate — the canonical (and
currently only) implementation of the interface defined in
[`../candidate_interface.py`](../candidate_interface.py).

The candidate ignores its input and always returns the same
hard-coded PlantUML block (a tiny library with `Book`, `Author`,
`Library` classes and two associations).

```
Candidates/dummy_candidate/
├── README.md         # this file
├── candidate.py      # exposes `candidate` (a DummyCandidate instance)
├── metric.json       # declares default scoring metric (metrik-1)
└── run.py            # per-candidate driver
```

## Default metric

This candidate ships a `metric.json` declaring `metrik-1` as its
default scoring metric. The driver reads it automatically when the
user does not pass `--metric` on the CLI.

```json
{
  "default_metric": "metrik-1"
}
```

To score with a different metric, pass it explicitly:

```bash
PYTHONPATH=. python Candidates/dummy_candidate/run.py \
    --dataset kaiser_clean \
    --metric metrik-4
```

## Why

- **Pipeline smoke-test.** Exercise
  `Workflow/Benchmark-Workflow/generate.py → .../score.py → .../visualise.py`
  end-to-end without LLM latency or Ollama running.
- **Schema inspection.** Open the produced JSON and see exactly what
  shape every record has.
- **Metric plumbing sanity-check.** Scoring the same PUML against
  every reference gives a deterministic per-record score pattern.

## Usage

```bash
# Run the full pipeline against the dummy (metric defaults to metrik-1).
# All artefacts land in Workflow/Results/dummy_candidate/.
PYTHONPATH=. python Candidates/dummy_candidate/run.py \
    --dataset kaiser_clean

# Run against the smaller reference set
PYTHONPATH=. python Candidates/dummy_candidate/run.py \
    --dataset reference_clean

# Or step-by-step (the driver just chains these calls in order):
PYTHONPATH=. python Workflow/Benchmark-Workflow/generate.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean --limit 3 \
    --out Workflow/Results/dummy_candidate/kaiser_clean.json

PYTHONPATH=. python Workflow/Benchmark-Workflow/score.py \
    --in Workflow/Results/dummy_candidate/kaiser_clean.json \
    --metric metrik-1

PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in Workflow/Results/dummy_candidate/kaiser_clean_scored.json \
    --out-dir Workflow/Results/dummy_candidate \
    --metric metrik-1

# Aggregate both datasets in one visualisation (overwrite the
# per-dataset _bucket_*.csv / heatmap_*.png files for each dataset;
# _summary.csv / _errors.csv are regenerated):
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in 'Workflow/Results/dummy_candidate/*_scored.json' \
    --out-dir Workflow/Results/dummy_candidate \
    --metric metrik-1
```

## Layout

```
Candidates/dummy_candidate/
├── README.md         # this file
├── candidate.py      # exposes `candidate` (a DummyCandidate instance)
├── metric.json       # declares default scoring metric (metrik-1)
└── run.py            # driver (chains generate → score → visualise)
```
