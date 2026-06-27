# Workflow/

Drives every (strategy × model × dataset) combination, scores the outputs
with metrik-4, and produces per-cell JSONs + cross-candidate summaries
that the notebook consumes.

```
Workflow/
├── orchestrator.py        # runs candidates, writes raw JSONs
├── metric_runner.py       # scores raw JSONs, writes scored JSONs + summary + bucket tables
├── run_full.py            # one-shot CLI: runs orchestrator + metric_runner with a banner
├── Notebooks/
│   └── walkthrough.ipynb  # 6 sections: bucket tables, heatmaps, mean, errors, summary
└── Results/               # generated, gitignored
    ├── <strategy>__<model>/        # for LLM strategies
    │   ├── kaiser.json             # raw: id, nlt, ref, gen, failed, error
    │   ├── reference.json
    │   ├── kaiser_scored.json      # raw + scores + summary
    │   └── reference_scored.json
    ├── rule_based/                 # rule-based has no model
    │   ├── kaiser.json
    │   └── ...
    ├── _summary.csv                # long format (strategy, model, dataset, element)
    ├── _summary.json
    ├── _bucket_<dataset>_<element>.csv   # 6 tables — the headline deliverable
    └── _errors.csv                 # every record where failed=True
```

## Why no `__init__.py`?

This directory is intentionally NOT a Python package (no `__init__.py`).
The upstream `domain_model_metrics` package injects its
`Quantitative-Analysis/Workflow/` directory onto `sys.path` on import and
then does `from Workflow.metric_interface import ...`. If our local
`Workflow/` folder were a package and got imported first, Python's import
system would cache it under `sys.modules['Workflow']` and the upstream's
`Workflow` would never be resolved.

The fix is to use the top-level scripts `scripts/run_*.py` (or
`Workflow/run_full.py` directly) which import `domain_model_metrics`
BEFORE loading any of our Workflow/ files.

## Run the full benchmark

```bash
PYTHONPATH=. python Workflow/run_full.py
```

This:
1. Prints a banner listing groups / strategies / models / datasets.
2. Runs the orchestrator: every strategy × every model × every dataset.
3. Runs the metric_runner: scores every cell with metrik-4, writes
   bucket tables + error log.
4. Prints the output locations.

## Smoke test

```bash
PYTHONPATH=. python Workflow/run_full.py --smoke
```

Runs `rule_based` × 2 records × 2 datasets. Fast (~12s end-to-end,
includes metric scoring).

## Restrict scope

```bash
PYTHONPATH=. python Workflow/run_full.py --strategies text2uml-kaiser --models minimax
PYTHONPATH=. python Workflow/run_full.py --limit 3         # first 3 records per dataset
PYTHONPATH=. python Workflow/run_full.py --datasets kaiser
```

## Skip rules

Each strategy declares `skip_folders = (folder_name, ...)`. The
orchestrator filters these records BEFORE invoking the LLM. The
filtered records still count as `n_skipped` in the cell JSON.

| Strategy            | Skipped folders                              |
|---------------------|----------------------------------------------|
| `text2uml-kaiser/zero_shot`    | —                              |
| `text2uml-kaiser/one_shot`     | `AlphaInsurance`                |
| `text2uml-kaiser/few_shot`     | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `text2uml-kaiser/cot`          | —                              |
| `text2uml-kaiser/cot_domain`   | —                              |
| `zenodo/zero_shot`             | —                              |
| `zenodo/cot`                   | —                              |
| `rule_based`                   | —                              |

## Failure handling

`Strategy.run()` returns `StrategyResult(puml="", error="...", raw="...")`
on any failure. The orchestrator catches all exceptions, records the
failure, and moves to the next record. **No retries** — the first failure
is final.

Failed records:
* appear in the cell JSON with `failed=True` and `error=<message>`;
* contribute to `n_failed` in the cell summary;
* score as zero in the metric (with `error` propagated);
* are listed in `_errors.csv` with strategy, model, dataset, id, error,
  and a 200-char `raw_excerpt` of the LLM output for debugging.

## Per-cell record schema

```json
{
  "strategy":         "zero_shot",
  "strategy_group":   "text2uml-kaiser",
  "model":            "minimax",
  "model_id":         "ollama/minimax-m3:cloud",
  "dataset":          "kaiser",
  "id":               "AirTravel",
  "nlt":              "...",
  "reference_model":  "@startuml\n...\n@enduml",
  "generated_model":  "@startuml\n...\n@enduml",
  "failed":           false,
  "error":            null,
  "raw_excerpt":      "...",
  "elapsed_seconds":  41.2,
  "scores": {
    "class_score": 0.81, "attribute_score": 0.84, "association_score": 0.75,
    "parse_warning_ref": [], "parse_warning_gen": [], "error": null
  }
}
```

## Bucket table schema (`_bucket_<dataset>_<element>.csv`)

```csv
strategy,model,n,n_failed,"[0, 0.1)","[0.1, 0.2)","[0.2, 0.3)","[0.3, 1.0]",mean,median
zero_shot,glm,45,3,12,15,10,5,0.21,0.18
zero_shot,kimi,45,1,18,12,9,5,0.16,0.13
...
rule_based,-,45,0,28,10,5,2,0.09,0.06
```

Rows are `(strategy, model)` pairs; columns are bucket counts plus
`n_failed`, `mean`, `median`. The same data is visualised in the notebook
as heatmaps (cell intensity = record count).