# Workflow/

Operational layer of the benchmark. The `Workflow/` folder contains
the pipeline scripts, the analysis notebook, and the auto-populated
output directory.

```
Workflow/
├── README.md                       # this file
├── Benchmark-Workflow/             # ← pipeline scripts (3 step files)
├── Notebooks/
│   └── walkthrough.ipynb           # consumes the artefacts from the pipeline
└── Results/                        # generated, gitignored
```

---

## The pipeline

Three independent step scripts live in
[`Workflow/Benchmark-Workflow/`](Benchmark-Workflow/README.md):

1. `generate.py` — candidate × dataset → raw JSON.
2. `score.py` — raw JSON → scored JSON (with metrik-1 … metrik-5).
3. `visualise.py` — scored JSON(s) → bucket tables + heatmaps.

You don't usually call them directly. The per-group drivers
(`Candidates/<group>/run-candidate.py`) chain them in order and
default the paths. See
[`Workflow/Benchmark-Workflow/README.md`](Benchmark-Workflow/README.md)
for the architecture, the `Candidate` Protocol, and the failure
handling contract.

---

## Quick recipe

```bash
export OLLAMA_MODEL=glm-5.1:cloud
ollama serve &

# 1. Run a strategy (the per-group driver does steps 1, 2, 3 for you).
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/run-candidate.py \
    --strategy zenodo_zero_shot \
    --dataset kaiser_clean --limit 3

# 2. (Optional) Re-run the visualiser against an existing run.
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in 'Workflow/Results/zenodo_zero_shot_*/*_scored.json' \
    --out-dir Workflow/Results/_aggregate \
    --metric metrik-4

# 3. Open the analysis notebook.
jupyter lab Workflow/Notebooks/walkthrough.ipynb
```

---

## Where to read more

- [`Workflow/Benchmark-Workflow/README.md`](Benchmark-Workflow/README.md) —
  the pipeline architecture reference.
- [`Candidates/adjustments.md`](../Candidates/adjustments.md) —
  the migration log.
- The per-group READMEs in `Candidates/<group>/README.md` — the
  operational surface for each group.
- The top-level [`../README.md`](../README.md) — the entry point.
