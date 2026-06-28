# automated-domainmodel-benchmark

[![CI](https://github.com/VasiliySeibert/Automated-DomainModel-Benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/VasiliySeibert/Automated-DomainModel-Benchmark/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

A reusable benchmark for **automated domain-modelling approaches**:

* **Data** — two PlantUML class-diagram corpora (45 + 8 models) with paired
  natural-language specifications.
* **Metric** — `metrik-4` from the FAIR4RS
  [`domain-model-metrics`](https://github.com/VasiliySeibert/domainModel-Metrics-Comparison)
  package, imported as a dependency (NOT copied).
* **Candidates** — 4 LLM candidates (GLM-5.1, Kimi-K2.6, Minimax-M3,
  Nemotron-3-Super) executed through `opencode run` in detached mode, plus
  a rule-based spaCy heuristic reused from `ai4se_benchmarkPaper`.
* **Workflow** — orchestrator + metric runner + 5-section walkthrough
  notebook (mean / bucket distribution / per-model heatmap / failure rate /
  summary table).

The repository is FAIR4RS-aligned: persistent identifiers via Zenodo,
rich metadata (CFF, CodeMeta), version-pinned dependencies, tests, and an
MIT license.

---

## Table of contents

1. [Quick start](#quick-start)
2. [Repository layout](#repository-layout)
3. [Datasets](#datasets)
4. [Candidates](#candidates)
5. [Metric](#metric)
6. [Workflow](#workflow)
7. [FAIR4RS mapping](#fair4rs-mapping)
8. [Citing](#citing)
9. [License](#license)

---

## Quick start

```bash
git clone https://github.com/VasiliySeibert/Automated-DomainModel-Benchmark
cd Automated-DomainModel-Benchmark

# Set up a venv (caller responsibility)
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e ".[dev,notebooks]"
python -m spacy download en_core_web_sm

# Optional: install the metric dependency if not already on your PYTHONPATH
pip install "git+https://github.com/VasiliySeibert/domainModel-Metrics-Comparison@v1.0.0"

# Regenerate the bundled datasets from their upstream sources
PYTHONPATH=. python Data/build_datasets.py

# Run the full benchmark (~30-90 min for the LLM portion)
PYTHONPATH=. python Workflow/run_full.py

# Or a fast smoke test (rule_based × 2 records × 2 datasets, ~12s)
PYTHONPATH=. python Workflow/run_full.py --smoke

# Inspect
jupyter lab Workflow/Notebooks/walkthrough.ipynb
```

## What is a "candidate"?

A *candidate* in this benchmark is a **prompt strategy**, not a model.
Eleven strategies in three groups:

| Group            | Strategy                | Source                                                                  |
|------------------|-------------------------|-------------------------------------------------------------------------|
| `text2uml-kaiser`| `zero_shot`             | `text2uml-kaiser/src/run.py::_ZERO_SHOT_SYSTEM`                         |
| `text2uml-kaiser`| `one_shot`              | `text2uml-kaiser/src/run.py::_PROMPT_ONE_SHOT` (skips AlphaInsurance)   |
| `text2uml-kaiser`| `few_shot`              | `text2uml-kaiser/src/run.py::_PROMPT_FEW_SHOT` (skips AlphaInsurance + GasStation) |
| `text2uml-kaiser`| `cot`                   | 5-step kaiser CoT chain (`_COT_*`)                                      |
| `text2uml-kaiser`| `cot_domain`            | 5-step CoT with explicit noun extraction (`_DOMAIN_*`)                  |
| `AutomatedDomainModelling_zenodo`| `zero_shot`    | `AutomatedDomainModelling_zenodo (the reconstruction in the local sibling repo) — see Candidates/AutomatedDomainModelling_zenodo/README.md` §1                        |
| `AutomatedDomainModelling_zenodo`| `one_shot_btms`| `…/prompts.md` §2 (skips BTMS)                                           |
| `AutomatedDomainModelling_zenodo`| `one_shot_h2s_short` | `…/prompts.md` §3 (skips H2S-Short + HelpingHands)               |
| `AutomatedDomainModelling_zenodo`| `two_shot`     | `…/prompts.md` §4 (skips BTMS + H2S-Short + HelpingHands)               |
| `AutomatedDomainModelling_zenodo`| `cot`          | `…/prompts.md` §5 (one-shot COT with H2S annotated example)             |
| `ai4se_benchmarkPaper` | `rule_based`   | `ai4se_benchmarkPaper/rule-based_candidate.ipynb` (no model)            |

Every LLM strategy is run against every model in
`Workflow/config.json` (`glm`, `kimi`, `minimax`, `nemotron`). Each
strategy is **fully self-contained** — `strategy.py` + `prompt*.txt` +
`examples.json` + `config.json` + `README.md` in its own folder.

Two harnesses:

* **`Candidates/ollama/`** (default) — direct HTTP POST to the local
  Ollama server's `/api/chat` endpoint.
* **`Candidates/opencode/`** (alternative) — subprocess wrapper around
  `opencode run` in detached mode.

Each strategy imports one harness at the top of `strategy.py`. Switch
is a one-line edit.

Cell count:

* **10 LLM strategies × 4 models × 2 datasets = 80 LLM cells**
* **+ 1 rule_based × 2 datasets = 2 cells**
* **= 82 records**

See [`Candidates/adjustments.md`](./Candidates/adjustments.md) for the
verbatim-vs-adapted audit.

## Repository layout

```
Automated-DomainModel-Benchmark/
├── Data/                              # two benchmark corpora + PlantUML parser
│   ├── kaiser.json                    # 45 synthetic domain models
│   ├── reference.json                 # 8 reference models
│   ├── build_datasets.py              # reproducible generator
│   └── Parser/                        # copied from domainModel-Metrics-Comparison
├── Metric/
│   └── wrapper.py                     # wraps domain-model-metrics.metrik-4
├── Candidates/                        # 11 self-contained prompt strategies
│   ├── ollama/                          # default LLM harness (HTTP)
│   ├── opencode/                        # alternative harness (subprocess)
│   ├── text2uml-kaiser/                 # 5 strategies (Kaiser 2026)
│   ├── AutomatedDomainModelling_zenodo/ # 5 strategies (Chen et al. 2023 (MODELS) — see Candidates/AutomatedDomainModelling_zenodo/README.md)
│   ├── ai4se_benchmarkPaper/            # 1 strategy: rule_based
│   ├── registry.py                      # walks the tree, builds spec list
│   └── adjustments.md                   # documents prompt changes vs upstream
├── Workflow/                          # orchestrator + scorer + notebook + run_full.py
│   ├── orchestrator.py                # runs every (strategy × model × dataset)
│   ├── metric_runner.py               # scores raw JSONs with metrik-4
│   ├── run_full.py                    # one-shot entrypoint with banner
│   ├── Notebooks/walkthrough.ipynb
│   └── Results/                       # generated, gitignored
├── scripts/
│   ├── run_orchestrator.py            # top-level CLI (avoids Workflow pkg shadow)
│   └── run_metric_runner.py
├── tests/                             # pytest: parser, metric wrapper, smoke
├── pyproject.toml                     # PEP 621 build + pinned deps
├── CITATION.cff                       # CFF 1.2.0
├── codemeta.json                      # CodeMeta 2.0
├── .zenodo.json                       # Zenodo deposit metadata
├── LICENSE                            # MIT
└── CHANGELOG.md                       # Keep-a-Changelog
```

## Datasets

| File                  | Source                                                                            | # Models |
|-----------------------|-----------------------------------------------------------------------------------|---------:|
| `Data/kaiser.json`    | [`text2uml-kaiser/dataset/<Model>/`](https://github.com/VasiliySeibert/text2uml-kaiser) |       45 |
| `Data/reference.json` | [`ReferenceModels-and-NLT/groundTruthWithPlantUML.json`](https://github.com/VasiliySeibert/ReferenceModels-and-NLT) |        8 |

Both share the schema `[{id, nlt, puml}, …]`. The local `Data/Parser/`
package (a verbatim copy of the parser shipped with `domain-model-metrics`)
parses 100 % of both datasets.

```bash
PYTHONPATH=. python Data/build_datasets.py   # regenerate
```

## Candidates

Eleven self-contained prompt strategies organised in three source
folders. Each strategy is fully self-contained: `strategy.py` + `prompt*.txt`
+ `examples.json` / `annotated_example.txt` + `config.json` + `README.md`.

| Strategy                              | Skip folders                              |
|---------------------------------------|-------------------------------------------|
| `text2uml-kaiser/zero_shot`           | —                                         |
| `text2uml-kaiser/one_shot`            | `AlphaInsurance`                          |
| `text2uml-kaiser/few_shot`            | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `text2uml-kaiser/cot`                 | —                                         |
| `text2uml-kaiser/cot_domain`          | —                                         |
| `AutomatedDomainModelling_zenodo/zero_shot`        | —                                |
| `AutomatedDomainModelling_zenodo/one_shot_btms`    | `BTMS`                       |
| `AutomatedDomainModelling_zenodo/one_shot_h2s_short` | `H2S-Short`, `HelpingHands` |
| `AutomatedDomainModelling_zenodo/two_shot`         | `BTMS`, `H2S-Short`, `HelpingHands` |
| `AutomatedDomainModelling_zenodo/cot`              | `H2S`, `H2S-Short`, `HelpingHands` |
| `ai4se_benchmarkPaper/rule_based`     | —                                         |

LLM strategies use direct Ollama HTTP (`Candidates/ollama/harness.py`).
The `Candidates/opencode/harness.py` subprocess wrapper is built but
unused by default. Each strategy imports its harness at the top of
`strategy.py` — switching is a one-line edit.

The kaiser CoT strategies chain 5 LLM calls; the others are
single-shot. The zenodo strategies emit a structured text response
that we post-process into PlantUML via
`AutomatedDomainModelling_zenodo/zenodo_text_format.py`.

All prompt adjustments vs the upstream suites are documented in
[`Candidates/adjustments.md`](./Candidates/adjustments.md).

## Metric

Imported (not copied) from the FAIR4RS `domain-model-metrics` v1.0.0
package — `metrik-4` is the recommended per-element pick:

| Element       | RQ1 (MAD) best | RQ2 (Pearson r) best |
|---------------|----------------|----------------------|
| Class         | metrik-5       | **metrik-4 (0.42)**  |
| Attribute     | **metrik-4**   | metrik-3 (0.65)      |
| Relationship  | metrik-1/3     | **metrik-4 (0.42)**  |

```python
from Metric import compute, summarise
scores = compute(ref_puml, gen_puml)        # 3 scores + parse warnings
summary = summarise([compute(r, g) for r, g in pairs])
print(summary["class_score"]["mean"], summary["class_score"]["buckets"])
```

## Workflow

```bash
# Run every (source × strategy × model × dataset) cell — one entrypoint
PYTHONPATH=. python Workflow/run_full.py

# Visualise
jupyter lab Workflow/Notebooks/walkthrough.ipynb
```

`Workflow/run_full.py` orchestrates the orchestrator + the metric runner
and prints a banner listing groups / strategies / models / datasets
before it begins. Output:

* `Workflow/Results/<source>/<strategy>__<model>/<dataset>.json` — raw outputs.
* `Workflow/Results/_bucket_<dataset>_<element>.csv` — 6 bucket tables
  (the headline deliverable, one per dataset × element).
* `Workflow/Results/_summary.csv` — long-format machine-readable table.
* `Workflow/Results/_errors.csv` — every record where `failed=True`.

The walkthrough notebook has 6 sections:

1. **Bucket tables** — the raw `_bucket_*.csv` files.
2. **Bucket heatmap** — `(strategy, model) × bucket` intensity grid per
   dataset × element.
3. **Mean score per (strategy, model)** — single-number comparison.
4. **Failure rate** — share of records where the strategy produced an
   empty PlantUML block.
5. **Error log** — every failed record with `raw_excerpt` for debugging.
6. **Cross-candidate summary** — the canonical `_summary.csv` sorted by
   mean score.

Failure handling: **no retries**. `Strategy.run()` returns a result
with `failed=True` and an error message on any failure; the orchestrator
records the failure and moves on. Every failed record appears in
`_errors.csv` with a 200-char excerpt of the LLM's raw output.

To run a subset:

```bash
# Only kaiser strategies
PYTHONPATH=. python Workflow/run_full.py --strategies text2uml-kaiser

# Only one model
PYTHONPATH=. python Workflow/run_full.py --models minimax

# Smoke (rule_based only, 2 records, ~12s)
PYTHONPATH=. python Workflow/run_full.py --smoke

# Limit records per dataset
PYTHONPATH=. python Workflow/run_full.py --limit 3
```

## FAIR4RS mapping

Modelled on the
[FAIR4RS principles](https://www.rd-alliance.org/group/fair-principles-research-software-working-group).
Each principle is mapped to a concrete artefact in this repository.

| FAIR4RS principle | Evidence in this repository |
|-------------------|------------------------------|
| **F1 / F1.1 / F1.2** PID, component IDs, version IDs | `CITATION.cff` (concept DOI badge in README); `.zenodo.json` triggers GitHub-Zenodo integration on each release tag. |
| **F2 / F3 / F4** rich, discoverable metadata | `CITATION.cff` (CFF 1.2.0); `codemeta.json` (CodeMeta 2.0); `pyproject.toml`; this README. |
| **A1 / A1.1** open retrieval | Public GitHub over HTTPS; `pip install -e ".[dev,notebooks]"` from source. |
| **A1.2** auth where needed | n/a — public repo. |
| **A2** metadata persistence | Zenodo deposit (F1); Software Heritage archive triggered automatically by each tag. |
| **I1 / I2** standards, qualified refs | CFF 1.2.0, CodeMeta 2.0, SPDX `MIT`, ORCID-qualified authorship, version-pinned `domain-model-metrics>=1.0.0`, PEP 621 build, PEP 561 `py.typed` marker. |
| **R1.1** clear license | [`LICENSE`](./LICENSE) — MIT (SPDX: `MIT`). |
| **R1.2** provenance | git history + [`CHANGELOG.md`](./CHANGELOG.md) (Keep-a-Changelog) + per-tag Zenodo DOIs. |
| **R1.3** community standards | CFF, CodeMeta, PEP 621, PEP 561. |
| **R2** qualified refs to other software | Version-pinned `domain-model-metrics` in `pyproject.toml`; `softwareRequirements` block in `codemeta.json`; `Software/requirements.txt` mirrors the pinned list. |
| **R3** community standards | GitHub Actions CI; CFF / CodeMeta / PEP 621. |
| **R3.1 / R3.2** tests, CI | `tests/` suite + `.github/workflows/ci.yml` (Python 3.11 + 3.12). |

## Citing

See [`CITATION.cff`](./CITATION.cff) — GitHub renders a "Cite this
repository" button on the sidebar that reads this file.

Cite the **concept DOI** (TBD after first Zenodo release) to identify the
project across all versions; cite the specific **version DOI** to identify
the exact snapshot you used.

Cite the metric dependency too:

```
Seibert, V. (2026). domain-model-metrics (v1.0.0). Zenodo.
https://doi.org/10.5281/zenodo.20942597
```

## License

`automated-domainmodel-benchmark` is released under the MIT License
(SPDX: `MIT`) — see [`LICENSE`](./LICENSE).