# Workflow/

This directory hosts benchmark outputs and the pipeline that produces
them.

```
Workflow/
├── README.md                       # this file
├── Benchmark-Workflow/             # the benchmark pipeline (three step scripts)
├── Notebooks/
│   └── walkthrough.ipynb           # consumes the output CSVs / heatmaps
└── Results/                        # generated, gitignored — see Workflow/Benchmark-Workflow/README.md
```

## Benchmark pipeline

The three steps (`generate.py`, `score.py`, `visualise.py`) live in
[`Workflow/Benchmark-Workflow/`](Benchmark-Workflow/). There is no
generic driver in `Workflow/` — each candidate ships its own driver
inside its own folder. See
[`Workflow/Benchmark-Workflow/README.md`](Benchmark-Workflow/README.md)
for the full pipeline reference and
[`Candidates/dummy_candidate/run.py`](../../Candidates/dummy_candidate/run.py)
for the worked example.

## Layout notes

- The outer `Workflow/` directory has **no** `__init__.py`; the
  package-shadow analysis is documented in
  [`Workflow/Benchmark-Workflow/README.md`](Benchmark-Workflow/README.md#why-the-outer-workflow-is-not-a-package).
- `Notebooks/walkthrough.ipynb` consumes `_summary.csv`,
  `_bucket_*.csv`, and `_errors.csv` produced by the visualiser step.
- `Results/` is generated and gitignored (except for `.gitkeep`-able
  placeholders). It is safe to delete and rebuild.
