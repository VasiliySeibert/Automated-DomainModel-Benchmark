# dummy_candidate

A **deterministic constant-output** Candidate — the canonical (and
currently only) implementation of the interface defined in
[`../candidate_interface.py`](../candidate_interface.py).

The candidate ignores its input and always returns the same
hard-coded PlantUML block (a tiny library with `Book`, `Author`,
`Library` classes and two associations).

## Default metric

This candidate ships a `metric.json` declaring `metrik-1` as its
default scoring metric. `Workflow/run_all.py` reads it automatically
when the user does not pass `--metric` on the CLI.

```json
{
  "default_metric": "metrik-1"
}
```

To score with a different metric, pass it explicitly:

```bash
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean \
    --metric metrik-4
```

## Why

- **Pipeline smoke-test.** Exercise
  `Workflow/generate.py → Workflow/score.py → Workflow/visualise.py`
  end-to-end without LLM latency or Ollama running.
- **Schema inspection.** Open the produced JSON and see exactly what
  shape every record has.
- **Metric plumbing sanity-check.** Scoring the same PUML against
  every reference gives a deterministic per-record score pattern.

## Usage

```bash
# Run the full pipeline against the dummy (metric defaults to metrik-1)
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean

# Or step-by-step:
PYTHONPATH=. python Workflow/generate.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean --limit 3 \
    --out Workflow/Results/dummy_candidate/kaiser_clean.json

PYTHONPATH=. python Workflow/score.py \
    --in Workflow/Results/dummy_candidate/kaiser_clean.json \
    --metric metrik-1

PYTHONPATH=. python Workflow/visualise.py \
    --in Workflow/Results/dummy_candidate/kaiser_clean_scored.json \
    --out-dir Workflow/Results \
    --metric metrik-1
```

## Layout

```
Candidates/dummy_candidate/
├── README.md         # this file
├── candidate.py      # exposes `candidate` (a DummyCandidate instance)
└── metric.json       # declares default scoring metric (metrik-1)
```