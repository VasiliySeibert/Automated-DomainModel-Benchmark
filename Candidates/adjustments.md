# Prompt & Logic Adjustments vs. Source Repositories

## Architecture rewrite (current)

The workflow has been re-architected around a `Candidate` interface:

```
Candidates/candidate_interface.py          # Protocol + loader + CandidateOutput
Candidates/dummy_candidate/                # canonical deterministic implementation
  ├── candidate.py
  ├── metric.json
  └── run.py                                # per-candidate driver (chains the three steps)
Workflow/Benchmark-Workflow/
  ├── generate.py                           # step 1: candidate × dataset → raw JSON
  ├── score.py                              # step 2: raw JSON → scored JSON
  └── visualise.py                          # step 3: scored JSON(s) → bucket tables + heatmaps
```

There is no generic driver at the workflow level. Each candidate
folder ships its own `run.py` (template:
`Candidates/dummy_candidate/run.py`) that chains the three step
scripts. Model iteration for LLM-driven candidates will live in the
candidate's constructor, not the workflow.

Each step is a standalone Python file. Each step's output is on disk
(JSON / CSV / PNG), so they can be inspected and re-run independently:

```bash
PYTHONPATH=. python Workflow/Benchmark-Workflow/generate.py  --candidate ... --dataset ... --out ...
PYTHONPATH=. python Workflow/Benchmark-Workflow/score.py     --in ...
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py --in '.../*_scored.json' --out-dir ...
```

Or end-to-end through the per-candidate driver:

```bash
PYTHONPATH=. python Candidates/dummy_candidate/run.py --dataset kaiser_clean
```

## What was removed

The following files were deleted as part of the rewrite:

- `Candidates/registry.py` — folder-walk + `SPEC` / `register()`
  machinery. Replaced by `load_candidate(path)` from the interface.
- `Workflow/orchestrator.py` — replaced by
  `Workflow/Benchmark-Workflow/generate.py`.
- `Workflow/metric_runner.py` — replaced by
  `Workflow/Benchmark-Workflow/score.py` and
  `Workflow/Benchmark-Workflow/visualise.py`.
- `Workflow/run_full.py` — replaced by `Workflow/run_all.py`.
- `Workflow/run_all.py` — replaced by per-candidate drivers at
  `Candidates/<candidate>/run.py` (the dummy's
  `Candidates/dummy_candidate/run.py` is the worked example).
- `tests/test_registry.py`, `tests/test_ollama_inlined.py`,
  `tests/test_kaiser_prompts.py`, `tests/test_zenodo_prompts.py`,
  `tests/test_rule_based.py` — coupled to the deleted registry.
  Replaced by `tests/test_candidate_interface.py` and the
  `tests/test_workflow_*.py` suite.

The 11 legacy strategies under `text2uml-kaiser/`,
`AutomatedDomainModelling_zenodo/`, and `ai4se_benchmarkPaper/rule_based/`
have had their module-level `SPEC = CandidateSpec(...)` and
`register(SPEC)` lines removed. Their `run()` functions are untouched
and will be migrated to the new interface in a follow-up step.

### rule_based — migrated

The non-LLM `Candidates/rule_based/` candidate has been migrated to
the new `Candidate` interface:

- `strategy.py` deleted; its normalisation logic (`_normalise`,
  `_CLASS_LINE`, `_REL_LINE`) inlined into `candidate.py`.
- New `candidate.py` exposes the module-level `candidate` callable
  wrapping the `RuleBasedCandidate` class.
- New `metric.json` declares `{"default_metric": "metrik-1"}`.
- New `run.py` is the per-candidate driver (template:
  `Candidates/dummy_candidate/run.py`) with
  `CANDIDATE_ID = "rule_based"`.
- `tests/test_rule_based_candidate.py` smoke-tests the driver
  end-to-end on `--limit 3` against `kaiser_clean`. Skipped when
  spaCy / `en_core_web_sm` are unavailable.

The other 11 LLM strategies under `text2uml-kaiser/` and
`AutomatedDomainModelling_zenodo/` remain on the legacy
`run(spec, nlt) -> dict` adapter; they will be migrated in a
follow-up step using the same shape.

## Migration of legacy strategies — TODO

Each legacy strategy needs:

1. A class wrapping its `run(spec, nlt) -> dict` function (or
   refactor `run` to take only `nlt` and pull sampling params from
   constructor arguments).
2. A module-level `candidate = MyClass(...)` instance.
3. A `candidate.py` filename (or a `__init__.py` shim that re-exports
   `candidate`).

Example shape:

```python
# Candidates/text2uml-kaiser/zero_shot/candidate.py
from .strategy import _run_impl
from Candidates.candidate_interface import CandidateOutput


class ZeroShotCandidate:
    def __init__(self, model: str, temperature: float = 0.7):
        self.model = model
        self.temperature = temperature

    def __call__(self, nlt: str) -> CandidateOutput:
        result = _run_impl(self.model, self.temperature, nlt)
        return CandidateOutput.from_dict(result)


candidate = ZeroShotCandidate(model="<default>")
```

The current dummy candidate is the canonical reference for the
expected shape.

---

## Original adjustment history (kept for traceability)

### 1. Fully self-contained candidates (pre-rewrite)

Per an earlier explicit requirement, every candidate folder was fully
self-contained — `strategy.py` + prompt files + `config.json` +
`README.md` + an inlined `_ollama.py` (byte-identical copy of the
Ollama `/api/chat` HTTP wrapper) for every LLM-driven strategy.

### 2. LLM access (inlined, pre-rewrite)

The LLM HTTP wrapper was previously a shared `Candidates/ollama/harness.py`
module and later a top-level `Harnesses/ollama/harness.py` module,
before finally being inlined into each strategy folder as `_ollama.py`
in Phase 5. The 10 inlined copies were guaranteed byte-identical by
`tests/test_ollama_inlined.py::test_all_10_inlined_ollama_copies_are_byte_identical`
(now deleted as part of the rewrite).

### 3. Discovery via `Candidates/registry.py` (pre-rewrite, deleted)

The registry walked the tree, dynamic-imported each `strategy.py`,
collected the `SPEC` / `register()` calls. Replaced by
`load_candidate(path)` in `Candidates/candidate_interface.py`.

### 4. Cell matrix (pre-rewrite)

11 strategies × 4 models × 2 datasets = 82 records (plus 2 for
rule_based). The new architecture is one candidate × one dataset per
`Candidates/<candidate>/run.py` invocation; model iteration (when
introduced for the legacy LLM strategies) will be driven by the
candidate's constructor, not the workflow.

### 5. Failure handling (unchanged)

`generate.py` catches every exception from the candidate and records
it as `{failed: True, error: "...", generated: ""}`. Failed records
appear in `_errors.csv` with a 200-char `raw_excerpt`.

### 6. Bucket boundaries (unchanged)

`Workflow/Results/_bucket_<dataset>_<element>.csv` (one per dataset ×
element). Score buckets: `[0, 0.1) / [0.1, 0.2) / [0.2, 0.3) / [0.3, 1.0]`.

### 7. FAIR4RS / metric dependency (unchanged)

The metric package (`domain-model-metrics`) is a separate pip-installable
artefact with its own Zenodo DOI
(`https://doi.org/10.5281/zenodo.20942597`). Citation remains required
when publishing benchmark results.

### 8. Metric selection (`--metric` flag)

The workflow accepts a `--metric` argument selecting which of the five
metriks (`metrik-1` … `metrik-5`) to score with. All five share the
same return-dict shape (`class_score`, `attribute_score`,
`association_score`, parse warnings, error) so `Metric.summarise()` and
the workflow steps work uniformly.

Resolution order in the per-candidate driver
(`Candidates/<candidate>/run.py`, see the dummy for the worked example):

1. `--metric` on the CLI.
2. `<candidate_folder>/metric.json` with shape
   `{"default_metric": "..."}`. The dummy candidate ships one
   declaring `metrik-1`.
3. Project default: `metrik-4`.

Output conventions:

- `Workflow/Benchmark-Workflow/score.py` writes the chosen metric
  into the scored JSON's `metric_name` field.
- `Workflow/Benchmark-Workflow/visualise.py` requires `--metric`,
  validates that every input JSON agrees, and suffixes bucket tables
  and heatmaps with `_<metric>`. Mixed-metric inputs are rejected
  with a clear error.
- `_summary.csv` and `_summary.json` gain a `metric` column / field.

Available metrics (also exposed as `Metric.METRIC_NAMES`):
`metrik-1`, `metrik-2`, `metrik-3`, `metrik-4`, `metrik-5`.