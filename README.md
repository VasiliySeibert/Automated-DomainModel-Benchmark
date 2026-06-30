# Automated DomainModel Benchmark

A benchmark for evaluating LLM-driven and rule-based UML class
diagram generation. 12 candidate strategies across 3 groups produce
PlantUML class diagrams from natural-language specifications, and
the results are scored against reference diagrams using the
`metrik-1` … `metrik-5` metric family.

A two-stage LLM pipeline (extract → translate → validate) is the
default for the 10 LLM-driven strategies. Two non-LLM strategies
(constant output and spaCy-based) provide baselines.

---

## Repository layout

```
.
├── README.md                          # this file
├── Candidates/                        # 12 candidate strategies
│   ├── candidate_interface.py         # the Candidate Protocol + load_candidate()
│   ├── plantuml_validator.py          # line-by-line PUML validator (auto-repair)
│   ├── AutomatedDomainModelling_zenodo/  # 5 zenodo strategies (Chen et al. 2023)
│   │   ├── run-candidate.py           # the zenodo group driver
│   │   ├── README.md
│   │   ├── zero_shot/
│   │   ├── one_shot_btms/
│   │   ├── one_shot_h2s_short/
│   │   ├── two_shot/
│   │   └── cot/
│   ├── text2uml-kaiser/                # 5 kaiser strategies (Calamo et al. 2025)
│   │   ├── run-candidate.py           # the kaiser group driver
│   │   ├── README.md
│   │   ├── zero_shot/
│   │   ├── one_shot/
│   │   ├── few_shot/
│   │   ├── cot/
│   │   └── cot_domain/
│   ├── rule_based/                     # non-LLM baseline (Abdelnabi et al. 2020)
│   │   ├── run.py                     # self-contained driver
│   │   └── ...
│   ├── dummy_candidate/                # non-LLM baseline (constant output)
│   │   ├── run.py                     # self-contained driver
│   │   └── ...
│   └── adjustments.md                   # the migration log
├── Workflow/
│   ├── README.md                       # directory-level orientation
│   ├── Benchmark-Workflow/             # the three pipeline step scripts
│   │   ├── generate.py                 # step 1: candidate × dataset → raw JSON
│   │   ├── score.py                    # step 2: raw JSON → scored JSON
│   │   ├── visualise.py                # step 3: scored JSON(s) → bucket tables + heatmaps
│   │   └── README.md                   # the pipeline architecture reference
│   ├── Notebooks/
│   │   └── walkthrough.ipynb           # consumes the output CSVs / heatmaps
│   └── Results/                        # generated, gitignored
└── domain_model_metrics (pip)          # the 5 metrik implementations
```

The `__init__.py` files in `Candidates/` and its subfolders are
load-bearing — without them, the import system can't find the
candidate modules. Do not delete them.

---

## Quick start

Run a smoke test of the zero-shot LLM strategy on 3 records:

```bash
export OLLAMA_MODEL=glm-5.1:cloud   # or any of the 4 cloud tags
ollama serve &                      # must be running

PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/run-candidate.py \
    --strategy zenodo_zero_shot \
    --dataset kaiser_clean --limit 3
```

The output lands in a single auto-named folder under
`Workflow/Results/`:

```
Workflow/Results/zenodo_zero_shot_glm-5.1_cloud_kaiser_clean_<UTC-timestamp>/
```

containing `kaiser_clean.json` (raw generate output),
`kaiser_clean_scored.json` (with metrik scores), `_summary.csv`,
`_bucket_*.csv`, `_errors.csv`, and `heatmap_*.png`.

Visualise with:

```bash
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in 'Workflow/Results/zenodo_zero_shot_*/*_scored.json' \
    --out-dir Workflow/Results/_aggregate/zenodo_zero_shot \
    --metric metrik-4
```

For richer analysis (bucket tables, per-candidate heatmaps, mean
bars, failure-rate bars, raw error logs), open
`Workflow/Notebooks/walkthrough.ipynb`.

---

## Available strategies

### Zenodo (Chen et al. 2023) — 2-stage LLM with translation prompt

These strategies ask the LLM to extract the domain model in a
zenodo-DSL format (`Enumerations:` / `Class:` / `Relationships:`
sections), then a second LLM call translates the DSL into canonical
PlantUML. The final PUML is validated line-by-line.

| `--strategy` | Description | Skip folders |
|---|---|---|
| `zenodo_zero_shot` | zero-shot prompt | — |
| `zenodo_one_shot_btms` | one-shot with BTMS example | `BTMS` |
| `zenodo_one_shot_h2s_short` | one-shot with H2S-Short | `H2S-Short`, `HelpingHands` |
| `zenodo_two_shot` | two-shot (BTMS + H2S-Short) | `BTMS`, `H2S-Short`, `HelpingHands` |
| `zenodo_cot` | chain-of-thought with H2S annotated | `H2S`, `H2S-Short`, `HelpingHands` |

Driver: `Candidates/AutomatedDomainModelling_zenodo/run-candidate.py`
Group README: `Candidates/AutomatedDomainModelling_zenodo/README.md`

### Kaiser (Calamo et al. 2025) — 1-stage LLM with validator

These strategies ask the LLM to produce a PlantUML class diagram
directly. The raw output is validated line-by-line before being
returned.

| `--strategy` | Description | Skip folders |
|---|---|---|
| `kaiser_zero_shot` | zero-shot | — |
| `kaiser_one_shot` | one-shot with AlphaInsurance | `AlphaInsurance` |
| `kaiser_few_shot` | few-shot (2 examples) | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `kaiser_cot` | 5-step chain-of-thought | — |
| `kaiser_cot_domain` | 5-step domain-aware CoT | — |

Driver: `Candidates/text2uml-kaiser/run-candidate.py`
Group README: `Candidates/text2uml-kaiser/README.md`

### Non-LLM baselines

| Strategy | Description | Driver |
|---|---|---|
| `rule_based` | spaCy-based extraction (Abdelnabi et al. 2020) | `Candidates/rule_based/run.py` |
| `dummy_candidate` | constant output (smoke test baseline) | `Candidates/dummy_candidate/run.py` |

The two non-LLM candidates have their own self-contained `run.py`
files rather than going through the per-group `run-candidate.py`
drivers. They have no LLM sampling flags.

---

## Datasets

Two datasets are bundled under `Data/`:

- `kaiser_clean` — 45 records from the kaiser upstream (the larger
  of the two). Aliased as `data-source-1`.
- `reference_clean` — 8 records. Aliased as `data-source-2`.

`--dataset kaiser_clean` and `--dataset data-source-1` are
equivalent. The `data-source-N` aliases exist for compatibility
with the upstream kaiser code.

---

## Metrics

The benchmark uses the `metrik-1` … `metrik-5` family from the
`domain-model-metrics` pip package. All five return three
sub-scores: `class_score`, `attribute_score`, `association_score`,
each in `[0, 1]`. The default per-candidate is `metrik-1` (from
each strategy's `metric.json`), falling back to `metrik-4` at the
project level.

Select with `--metric`:

```bash
--metric metrik-1
--metric metrik-4
```

The `domain-model-metrics` package is a separate pip-installable
artefact with its own Zenodo DOI
([10.5281/zenodo.20942597](https://doi.org/10.5281/zenodo.20942597)).
Citation is required when publishing benchmark results.

---

## Output folder shape

When `--results-dir` is not set, the per-group drivers write to an
auto-named folder:

```
Workflow/Results/<CANDIDATE_ID>_<model_sanitized>_<dataset>_<timestamp>/
```

where:
- `<CANDIDATE_ID>` is the `--strategy` value (e.g. `zenodo_zero_shot`).
- `<model_sanitized>` is the Ollama model tag with filesystem-unsafe
  characters replaced (e.g. `glm-5.1:cloud` → `glm-5.1_cloud`).
- `<dataset>` is the `--dataset` value.
- `<timestamp>` is `YYYY-MM-DDTHH-MM-SSZ` UTC at the time of invocation.

`--name SUFFIX` appends `_<SUFFIX>` to the basename for ad-hoc
disambiguation. `--results-dir PATH` bypasses the auto-named default
entirely.

Every invocation produces a unique folder, so re-runs with
different model or sampling parameters never clobber each other.
Two invocations within the same second produce the same folder
name; the second overwrites the first.

The folder contains 10 artefacts per run: `<dataset>.json` (raw
generate), `<dataset>_scored.json` (with metrik scores),
`_summary.csv`, `_summary.json`, three `_bucket_*.csv`, one
`_errors.csv`, and three `heatmap_*.png`.

---

## Failure modes

The candidate's `__call__` returns a `CandidateOutput` with
`failed: True` and an `error` string when something goes wrong. The
full taxonomy of error strings:

| `error` string | Cause |
|---|---|
| `exception: <class>: <msg>` | The Ollama call raised (e.g. `ConnectionError`). |
| `*_no_plantuml` | The LLM response had no `@startuml…@enduml` block. |
| `*_no_classes` / `*_step*_no_classes` | CoT step 1 or 2 returned no parseable class list. |
| `plantuml_validator: <errors>` | The validator rejected the final PUML. |

Failed records are still scored (the metrik-4 parser handles
partial diagrams gracefully) and surface in `<out-dir>/_errors.csv`
with a 200-char `raw_excerpt`. The full `generated_model` field
(after auto-repair) is in the scored JSON.

The validator auto-repairs mechanical issues (missing `class`
keyword, unquoted cardinalities, referenced-but-undeclared classes)
and surfaces non-mechanical issues (unrecognised line kinds,
invalid identifiers) as `plantuml_validator: <errors>`. See
`Candidates/AutomatedDomainModelling_zenodo/plantuml_validator.py`
for the full contract.

---

## How to visualise results

After a scored run, the visualiser at
`Workflow/Benchmark-Workflow/visualise.py` produces summary tables
and heatmaps. Examples:

```bash
# One strategy, one dataset.
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in 'Workflow/Results/zenodo_zero_shot_*/*_scored.json' \
    --out-dir Workflow/Results/_aggregate/zenodo_zero_shot \
    --metric metrik-4

# All zenodo strategies, all datasets.
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in 'Workflow/Results/zenodo_*/*_scored.json' \
    --out-dir Workflow/Results/_aggregate/zenodo \
    --metric metrik-4

# All LLM strategies, one metric.
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in 'Workflow/Results/{zenodo,kaiser}_*/*_scored.json' \
    --out-dir Workflow/Results/_aggregate/llm \
    --metric metrik-4
```

The visualiser produces (in `--out-dir`):
- `_summary.csv` / `_summary.json` — cross-strategy aggregation.
- `_bucket_<dataset>_<element>_<metric>.csv` — score histograms.
- `_errors.csv` — failure log.
- `heatmap_<dataset>_<element>_<metric>.png` — per-(dataset, element) heatmap.

The `--in` flag accepts a glob. Mixing scored JSONs that disagree
on `--metric` raises a clear error.

For richer analysis (bucket tables with formatting, per-candidate
heatmaps side-by-side, mean-score bars, failure-rate bars, raw
error logs), use `Workflow/Notebooks/walkthrough.ipynb` which
consumes the same artefacts. The notebook uses the `candidate`
column (not `strategy`/`model`) throughout for cross-candidate
comparisons.

---

## LLM sampling

The 10 LLM-driven strategies all share the same sampling parameter
resolution order (per flag):

1. CLI flag value (e.g. `--temperature 0.7`).
2. `OLLAMA_MODEL` env var (model only).
3. `<strategy-folder>/config.json` key.
4. Project default baked into the candidate.

Per-group default values (from each strategy's `config.json`):
- `temperature` = `0.7` (matches the upstream zenodo / kaiser papers).
- `num_predict` = `1024`.
- `timeout_seconds` = `600`.
- `seed`, `top_p`, `top_k`, `repeat_penalty` = unset (Ollama defaults).

The zenodo drivers have two extra flags (`--no-translate` and
`--temperature-translate`) that control the second LLM call. The
kaiser drivers don't have these flags because kaiser is single-stage.

The thinking-mode quirk: the four cloud tags available via Ollama
(`minimax-m3:cloud`, `glm-5.1:cloud`, `kimi-k2.6:cloud`,
`nemotron-3-super:cloud`) advertise `thinking` capability. When
the prompt is complex or the model decides to think at length, the
response is sometimes returned in `message.thinking` rather than
`message.content`. The inlined `_ollama.py` falls back to
`thinking` if `content` is empty. The non-cloud `qwen2.5-coder:7b`
model does not have this quirk.

---

## Adding a new strategy

1. Create a folder under `Candidates/<group>/` (or one of the
   existing groups) with:
   - `candidate.py` exposing a module-level `candidate` callable
     that conforms to the `Candidate` Protocol (returns
     `CandidateOutput`).
   - `config.json` (model/sampling defaults).
   - `metric.json` (`{"default_metric": "metrik-1"}`).
   - `_ollama.py` (inlined Ollama HTTP wrapper, if LLM-driven). Copy
     the extended version (8 kwargs + `message.thinking` fallback)
     from an existing strategy.
   - An empty `__init__.py` (load-bearing for the import system).
   - Prompt files (verbatim from the upstream source).
   - `README.md` (architecture, files, skip folders, failure modes,
     outputs).
2. Add the strategy to the appropriate per-group driver's
   `_STRATEGIES` table (the table maps `--strategy <name>` to
   `candidate_path: <folder-name>` and the skip folders).
3. Re-run the per-group driver's smoke test:
   ```bash
   python <group>/run-candidate.py --strategy <new_strategy> --dataset kaiser_clean --limit 3
   ```
4. Add a "migrated" block to `Candidates/adjustments.md` recording
   the smoke-test result.

For the architecture of the pipeline, see
[`Workflow/Benchmark-Workflow/README.md`](Workflow/Benchmark-Workflow/README.md).
For the migration log, see
[`Candidates/adjustments.md`](Candidates/adjustments.md).

---

## Sources

- **Chen, Yang, Chen, Hernández López, Mussbacher & Varró (2023)** —
  zenodo strategies. *Automated Domain Modeling with Large Language
  Models: A Comparative Study.* MODELS 2023.
  [DOI: 10.1109/MODELS58315.2023.00012](https://doi.org/10.1109/MODELS58315.2023.00012)
  · [Zenodo: 10.5281/zenodo.8105098](https://doi.org/10.5281/zenodo.8105098)
  License: CC BY 4.0.
- **Calamo, Mecella & Snoeck (2025)** — kaiser strategies. *Text2UML.*
  [github.com/IlKaiser/text2uml](https://github.com/IlKaiser/text2uml)
- **Abdelnabi, Maatuk, Abdelaziz & Elakeili (2020)** — `rule_based`.
  *Generating UML Class Diagram using NLP Techniques and Heuristic
  Rules.* STA 2020.
  [DOI: 10.1109/STA50679.2020.9329301](https://doi.org/10.1109/STA50679.2020.9329301)
- **`domain-model-metrics`** — the `metrik-1` … `metrik-5`
  implementations.
  [github.com/VasiliySeibert/domainModel-Metrics-Comparison](https://github.com/VasiliySeibert/domainModel-Metrics-Comparison)
  · [Zenodo: 10.5281/zenodo.20942597](https://doi.org/10.5281/zenodo.20942597)

---

## Where to read more

- [`Workflow/README.md`](Workflow/README.md) — directory-level
  orientation for the `Workflow/` folder.
- [`Workflow/Benchmark-Workflow/README.md`](Workflow/Benchmark-Workflow/README.md) — the
  pipeline architecture reference (the 3 step scripts, the
  `Candidate` interface, failure handling, the metric selection).
- [`Candidates/adjustments.md`](Candidates/adjustments.md) — the
  migration log, recording every architectural change since the
  rewrite.
- The per-group READMEs in `Candidates/<group>/README.md` — the
  operational surface for each group (flags, paths, failure modes,
  per-strategy details).
