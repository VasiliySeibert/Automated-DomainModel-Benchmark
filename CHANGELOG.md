# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-27

First public FAIR4RS release of the `automated-domainmodel-benchmark` package.

### Added
- Two benchmark datasets in `Data/`:
  - `kaiser.json` — 45 synthetic domain models (text2uml-kaiser corpus).
  - `reference.json` — 8 reference models (ReferenceModels-and-NLT corpus).
- `Data/Parser/` — a verbatim copy of the PlantUML parser from
  `domainModel-Metrics-Comparison`, repackaged as `Data.Parser`. 100 %
  parse coverage on both datasets (45/45 + 8/8).
- `Metric/wrapper.py` — a thin wrapper around `domain-model-metrics`
  v1.0.0 (`metrik-4`). Returns per-element scores plus parser warnings,
  with bucket boundaries `[0, 0.1) / [0.1, 0.2) / [0.2, 0.3) / [0.3, 1.0]`.
- **Two harnesses** in `Candidates/`:
  - `Candidates/ollama/` — default LLM harness. Direct HTTP POST to
    `/api/chat` on the local Ollama server.
  - `Candidates/opencode/` — alternative harness. Subprocess wrapper
    around `opencode run` in detached mode.
- **Eleven self-contained prompt strategies** organised in three source
  folders. Each strategy folder contains `strategy.py` + `prompt*.txt` +
  `examples.json` / `annotated_example.txt` + `config.json` + `README.md`:
  - `text2uml-kaiser/`: `zero_shot`, `one_shot`, `few_shot`, `cot`,
    `cot_domain` (5-step CoT chain).
  - `AutomatedDomainModelling_zenodo/`: `zero_shot`, `one_shot_btms`,
    `one_shot_h2s_short`, `two_shot`, `cot`.
  - `ai4se_benchmarkPaper/rule_based/`: spaCy SVO + verb-lemma heuristic.
- `Candidates/registry.py` — walks the tree, dynamically imports each
  `strategy.py` via `importlib.util.spec_from_file_location` (handles
  hyphens in folder names like `AutomatedDomainModelling_zenodo`).
- `Workflow/config.json` + `Workflow/config_loader.py` — model registry,
  datasets, metric name, score-bucket boundaries.
- `Workflow/orchestrator.py` + `Workflow/metric_runner.py` driven by
  the one-shot `Workflow/run_full.py` (banner lists groups / strategies
  / models / datasets).
- Per-cell failure handling: no retries, every failure recorded in
  `_errors.csv` with a `raw_excerpt` for debugging.
- `Workflow/Notebooks/walkthrough.ipynb` — 6 sections: bucket tables,
  bucket heatmap, mean per (strategy, model), failure rate, error log,
  cross-candidate summary.
- Headline outputs:
  - `Workflow/Results/_bucket_<dataset>_<element>.csv` (6 files).
  - `Workflow/Results/_summary.csv` (long format).
  - `Workflow/Results/_errors.csv`.
- FAIR4RS metadata: `LICENSE` (MIT), `CITATION.cff`, `codemeta.json`,
  `.zenodo.json`, `pyproject.toml`, CI on Python 3.11 + 3.12.

### Removed
- `Candidates/{glm,kimi,minimax,nemotron}/` — model is no longer a
  candidate axis; strategies are now model-agnostic and pick the model
  at runtime via `Workflow/config.json`.
- Shared `base.py`, `plan.py`, `execute.py`, `models.py`, `shared.py`
  modules in `Candidates/` — every candidate is now fully self-contained.
- The old `Models.MODELS` registry is replaced by `Workflow/config.json`.

### Notes
- Confirmed via two `@explore` agent reports that the kaiser repo
  defines exactly 5 strategies (`zero_shot`, `one_shot`, `few_shot`,
  `cot`, `cot_domain`) and the zenodo repo defines exactly 5 settings
  (`zero_shot`, `one_shot_BTMS`, `one_shot_H2S-Short`, `two_shot`,
  `cot`).
- Cell count: **82 records** (10 LLM strategies × 4 models × 2
  datasets + 1 rule_based × 2 datasets).
- Estimated full-run time: 30-90 minutes. Smoke test: ~12s.