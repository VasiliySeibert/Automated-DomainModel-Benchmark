# Session Summary

A chronological summary of everything we built in this session for the
`Automated-DomainModel-Benchmark` repository.

---

## Phase 1 — Initial scaffolding

Built the first cut of the benchmark:

- **Data/** — `kaiser.json` (45 models) + `reference.json` (8 models) +
  `Data/Parser/` (verbatim copy of the PlantUML parser from
  `domainModel-Metrics-Comparison`).
- **Metric/** — `wrapper.py` around `domain-model-metrics`'s `metrik-4`.
- **Candidates/** — first version had `Candidates/{glm,kimi,minimax,nemotron}/`
  with one candidate folder per **model** (the wrong axis — see Phase 3).
- **Workflow/** — `orchestrator.py` + `metric_runner.py` + walkthrough notebook.
- **scripts/run_*.py** — top-level shims to avoid `Workflow` package shadow.
- **FAIR4RS** files: `LICENSE`, `CITATION.cff`, `codemeta.json`, `.zenodo.json`,
  `CHANGELOG.md`, GitHub Actions CI.

First smoke test passed end-to-end. ~12 tests passed.

---

## Phase 2 — Restructure: strategies × models

You correctly pointed out that **the model isn't the candidate — the
prompt strategy is**. We restructured:

- Deleted `Candidates/{glm,kimi,minimax,nemotron}/` (model-axis was wrong).
- Created `Candidates/text2uml-kaiser/{zero_shot,one_shot,few_shot,cot,cot_domain}/`
  and `Candidates/zenodo/{zero_shot,cot}/`.
- Added `Candidates/models.py` (extracted from `shared.py`).
- Added `Candidates/base.py` (`Strategy` base class), `plan.py`,
  `execute.py` (kaiser CoT helpers).
- Created `Candidates/registry.py` exposing `ALL_STRATEGIES`,
  `STRATEGIES_BY_GROUP`, `GROUPS`.
- New bucket boundaries: `[0, 0.1) / [0.1, 0.2) / [0.2, 0.3) / [0.3, 1.0]`.
- Cell count: 7 LLM strategies × 4 models + 1 rule_based × 1 model =
  29 cells/dataset × 2 = 58 records.

49 tests passed. Full smoke + minimax LLM cell test both worked.

---

## Phase 3 — Final restructure: fully self-contained candidates

You said:
- "Don't have any shared code, every candidate should contain everything."
- "The opencode harness is a separate candidate."
- "The other strategies should use the models from ollama (traditional
  prompting)."
- "Use two `@explore` agents to explore the prompting strategies."
- "Rename the zenodo candidate to `AutomatedDomainModelling_zenodo`."

What we did:

### Dispatched two `@explore` agents in parallel

**Agent 1 (text2uml-kaiser):** Confirmed **5 strategies** in the
upstream:
- `zero_shot` (1 LLM call)
- `one_shot` (1 call, AlphaInsurance example)
- `few_shot` (1 call, AlphaInsurance + GasStation examples)
- `cot` (5-call chain: class list → assoc+inherit → attrs → cardinalities → PlantUML)
- `cot_domain` (5-call chain, different first step: nouns → class list → ...)

Reported file paths + line numbers for every prompt constant.

**Agent 2 (AutomatedDomainModelling_zenodo):** Confirmed **5 settings**:
- `zero_shot` (no examples, text format)
- `one_shot_btms` (BTMS example, text format)
- `one_shot_h2s_short` (H2S-Short example, text format)
- `two_shot` (BTMS + H2S-Short, text format)
- `cot` (one-shot, H2S annotated example)

Confirmed via `Round 1 Evaluation/first_round.csv`, `Round 2 Evaluation/
second_round.csv`, and the 5×3 = 15 saved result XLSX files.

### Restructured the candidates tree

Deleted all shared modules (`base.py`, `plan.py`, `execute.py`,
`models.py`, `shared.py`). New layout:

```
Candidates/
├── ollama/                              # default LLM harness (HTTP)
│   ├── harness.py                       # POST $OLLAMA_HOST/api/chat
│   ├── config.json
│   └── README.md
├── opencode/                            # alternative harness (subprocess)
│   ├── harness.py                       # shells out to `opencode run`
│   ├── config.json
│   └── README.md
├── text2uml-kaiser/                     # 5 strategies
│   ├── zero_shot/    {strategy.py, prompt.txt, config.json, README.md}
│   ├── one_shot/     {strategy.py, prompt.txt, examples.json, config.json, README.md}
│   ├── few_shot/     {strategy.py, prompt.txt, examples.json, config.json, README.md}
│   ├── cot/          {strategy.py, prompt_step{1,2,2b,3,5}_*.txt, config.json, README.md}
│   └── cot_domain/   {strategy.py, prompt_step{1,2,3,2b,5}_*.txt, config.json, README.md}
├── AutomatedDomainModelling_zenodo/     # 5 strategies (renamed with dashes)
│   ├── zero_shot/         {strategy.py, prompt_{system,task}.txt, config.json, README.md}
│   ├── one_shot_btms/     {strategy.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── one_shot_h2s_short/{strategy.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── two_shot/          {strategy.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── cot/               {strategy.py, prompt_{system,task}.txt, annotated_example.txt, ...}
│   └── zenodo_text_format.py  # source-group-shared helper
├── ai4se_benchmarkPaper/
│   └── rule_based/      {strategy.py, heuristic.py, config.json, README.md}
├── registry.py                          # walks the tree via importlib
└── adjustments.md
```

Each candidate is fully self-contained: `strategy.py` + `prompt*.txt` +
`examples.json` / `annotated_example.txt` + `config.json` + `README.md`.

### Key implementation details

- `Candidates/registry.py` uses `importlib.util.spec_from_file_location`
  to load strategy modules dynamically — this is necessary because the
  folder `AutomatedDomainModelling_zenodo` contains hyphens (not legal
  in Python module names).
- Each strategy imports one harness at the top of `strategy.py`:
  ```python
  from Harnesses.ollama.harness import call as call_llm
  ```
  Switching to opencode is a one-line edit per strategy.
- The default harness is **ollama** (direct HTTP, 2-3× faster than
  opencode for the same model).
- The ollama harness is configurable via `$OLLAMA_HOST` (default
  `http://localhost:11434`).
- Brace fixup: every `{{` → `{` and `}}` → `}` in the upstream kaiser
  prompts (LangChain's brace-escape syntax) was collapsed to single
  braces in the per-strategy prompt files.

### Workflow updated

- New `Workflow/config.json` holds the model registry:
  ```json
  {"models": [{"short": "glm", "model_id": "glm-5.1:cloud", ...}, ...]}
  ```
- New `Workflow/config_loader.py` provides typed accessors.
- `Workflow/orchestrator.py` walks every `(source, strategy, model, dataset)`
  cell and writes `Results/<source>/<strategy>__<model>/<dataset>.json`.
- `Workflow/metric_runner.py` reads those JSONs and produces
  `_bucket_<dataset>_<element>.csv` (6 tables), `_summary.csv`,
  `_summary.json`, `_errors.csv`.
- `Workflow/run_full.py` is the one-shot entrypoint with a banner.
- Output layout is now deeper: `Results/<source>/<strategy>__<model>/<dataset>.json`.

### Cell count: **82 records**

- 10 LLM strategies × 4 models × 2 datasets = **80 LLM cells**
- 1 rule_based × 2 datasets = **2 cells**
- **Total: 82 records**

### Skip rules

| Strategy                                    | Skipped folders                                       |
|---------------------------------------------|------------------------------------------------------|
| `text2uml-kaiser/one_shot`                  | `AlphaInsurance`                                      |
| `text2uml-kaiser/few_shot`                  | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `AutomatedDomainModelling_zenodo/one_shot_btms`   | `BTMS`                                          |
| `AutomatedDomainModelling_zenodo/one_shot_h2s_short` | `H2S-Short`, `HelpingHands`               |
| `AutomatedDomainModelling_zenodo/two_shot`   | `BTMS`, `H2S-Short`, `HelpingHands`                   |
| `AutomatedDomainModelling_zenodo/cot`        | `H2S`, `H2S-Short`, `HelpingHands`                   |

### Bucket tables

`Workflow/Results/_bucket_<dataset>_<element>.csv` (6 files):

```
source, strategy, model, n, n_failed, [0, 0.1), [0.1, 0.2), [0.2, 0.3), [0.3, 1.0], mean, median
text2uml-kaiser, zero_shot, glm, 45, 3, 12, 15, 10, 5, 0.21, 0.18
...
rule_based, rule_based, -, 45, 0, 28, 10, 5, 2, 0.09, 0.06
```

### Tests rewritten

- `tests/test_registry.py` — 9 tests for the candidate registry.
- `tests/test_ollama_harness.py` — 5 tests for the ollama HTTP harness
  (mocked with `responses`).
- `tests/test_opencode_harness.py` — 3 tests for the opencode subprocess.
- `tests/test_rule_based.py` — 3 tests for the rule-based strategy.
- `tests/test_kaiser_prompts.py` — 7 tests for the kaiser prompt files.
- `tests/test_zenodo_prompts.py` — 7 tests for the zenodo prompt files.
- Plus retained: `tests/test_data_smoke.py` (5), `tests/test_metric_wrapper.py` (7).

**44 tests pass.**

### Smoke + LLM test

- **Smoke** (`Workflow/run_full.py --smoke`): rule_based × 2 datasets ×
  2 records, ~12s. Produces 2 cells + bucket tables + summary + errors.
- **LLM cell** (`text2uml-kaiser/zero_shot × minimax × kaiser`):
  minimax took 21s for one record and emitted a valid PlantUML block.
  Scored 0.82/0.84/0.76 across class/attribute/association.

### Failure handling

**No retries.** `Strategy.run()` returns `{generated_model, failed,
error, raw_excerpt}`. The orchestrator catches all exceptions and
records failures. Failed records appear in `_errors.csv` with
`{source, strategy, model, dataset, id, error, raw_excerpt}` (200-char
excerpt of the LLM's raw output for debugging).

---

## Files created/modified across all phases

```
LICENSE                                       # MIT, copied from upstream
CITATION.cff                                  # CFF 1.2.0
codemeta.json                                 # CodeMeta 2.0
.zenodo.json                                  # Zenodo deposit metadata
pyproject.toml                                # PEP 621
requirements.txt
environment.yml
CHANGELOG.md
README.md
.gitignore
.zenodo.json
.github/workflows/ci.yml                      # Python 3.11 + 3.12

Data/
├── kaiser.json                               # 45 models
├── reference.json                            # 8 models
├── build_datasets.py
├── Parser/                                   # copied from domainModel-Metrics-Comparison
└── README.md

Metric/
├── wrapper.py                                # metrik-4 wrapper, bucket boundaries
├── __init__.py
└── README.md

Candidates/
├── ollama/{harness.py, config.json, README.md}
├── opencode/{harness.py, config.json, README.md}
├── text2uml-kaiser/
│   ├── config.json, README.md
│   ├── zero_shot/{strategy.py, prompt.txt, config.json, README.md}
│   ├── one_shot/{strategy.py, prompt.txt, examples.json, config.json, README.md}
│   ├── few_shot/{strategy.py, prompt.txt, examples.json, config.json, README.md}
│   ├── cot/{strategy.py, prompt_step{1,2,2b,3,5}_*.txt, config.json, README.md}
│   └── cot_domain/{strategy.py, prompt_step{1,2,3,2b,5}_*.txt, config.json, README.md}
├── AutomatedDomainModelling_zenodo/
│   ├── config.json, README.md
│   ├── _examples_btms.py
│   ├── zenodo_text_format.py
│   ├── zero_shot/{strategy.py, prompt_{system,task}.txt, config.json, README.md}
│   ├── one_shot_btms/{strategy.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── one_shot_h2s_short/{strategy.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── two_shot/{strategy.py, prompt_{system,task}.txt, examples.json, ...}
│   └── cot/{strategy.py, prompt_{system,task}.txt, annotated_example.txt, ...}
├── ai4se_benchmarkPaper/
│   ├── config.json, README.md
│   └── rule_based/{strategy.py, heuristic.py, config.json, README.md}
├── registry.py                              # walks the tree, builds spec list
└── adjustments.md

Workflow/
├── config.json                               # model registry, datasets, metric
├── config_loader.py                          # typed accessors
├── orchestrator.py                           # runs every cell
├── metric_runner.py                          # scores + bucket tables
├── run_full.py                               # one-shot entrypoint
├── README.md
└── Notebooks/walkthrough.ipynb

scripts/
├── run_orchestrator.py                       # top-level CLI shim
└── run_metric_runner.py

tests/
├── conftest.py
├── test_data_smoke.py                        # 5 tests
├── test_metric_wrapper.py                    # 7 tests
├── test_registry.py                          # 9 tests
├── test_ollama_harness.py                    # 5 tests
├── test_opencode_harness.py                  # 3 tests
├── test_rule_based.py                        # 3 tests
├── test_kaiser_prompts.py                    # 7 tests
└── test_zenodo_prompts.py                    # 7 tests
```

Total: **44 tests passing.**

---

## To run the benchmark

```bash
# Activate venv (caller does this before running us)
source .venv/bin/activate

# Full run: 82 cells, 30-90 minutes
PYTHONPATH=. python Workflow/run_full.py

# Smoke: rule_based × 2 datasets × 2 records, ~12s
PYTHONPATH=. python Workflow/run_full.py --smoke

# Inspect results
jupyter lab Workflow/Notebooks/walkthrough.ipynb
```

The walkthrough notebook has 6 sections: bucket tables, bucket heatmaps,
mean per (strategy, model), failure rate, error log, and the canonical
`_summary.csv` cross-candidate summary.

---

## Phase 4 — Faithful zenodo reproduction + output translation

You said: "I am a bit worried about the naming its too generic. Lets
have a look at the reference repositories again. Lets make sure that we
adapt their approach exactly ... then we can think about translating
their output so that it matches with the /Data/Parser."

### What we changed

- **Renamed `AutomatedDomainModelling_zenodo/` →
  `AutomatedDomainModelling_zenodo/`** (underscores). The hyphenated
  name is not Python-importable; the underscore form lets the helper
  be imported as a normal package
  (`from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format
  import text_to_plantuml`). The original source-repo name is
  preserved in `Candidates/AutomatedDomainModelling_zenodo/__init__.py`
  as a comment for provenance.
- **Added `_messages.py` helper** in the zenodo source group that
  flattens an upstream chat-form `[{role, content}, …]` list into the
  `(system, user)` pair the ollama harness accepts, preserving the
  multi-turn structure with `USER:` / `ASSISTANT:` labels.
- **Refactored all 5 zenodo strategies** (`zero_shot`, `one_shot_btms`,
  `one_shot_h2s_short`, `two_shot`, `cot`) to build upstream-style chat
  message lists via `generate_prompts_chatgpt` /
  `generate_prompts_chatgpt_COT` patterns, then flatten and send.
- **Added `temperature` + `num_predict` to the ollama harness** and to
  `CandidateSpec`. All 5 zenodo strategies pass the upstream
  `temperature=0.7, num_predict=1024` defaults.
- **Comprehensive rewrite of `zenodo_text_format.py`**:
  - Accepts both singular and plural headings (`Class:` / `Classes:`,
    `Enumeration` / `Enumerations`, etc.).
  - Accepts `inherit` *and* `isA` for inheritance (the CoT H2S
    annotated example uses both).
  - Tolerates markdown code fences and leading prose.
  - Emits quoted cardinalities (`"1"`, `"*"`, `"0..*"`).

### Cleanup

- Deleted `Candidates/AutomatedDomainModelling_zenodo/_examples_btms.py`
  (orphan script — the BTMS data lives in `examples.json`).
- Removed all `__pycache__/` directories and stale `.pyc` files (git
  already ignores them but they were confusing `discover()`).

### Tests

- Added 12 new tests in `tests/test_zenodo_prompts.py`:
  - `text_to_plantuml` round-trip for BTMS through `Data.Parser`.
  - `isA` verb handling.
  - Plural heading tolerance.
  - Markdown fence tolerance.
  - Leading-prose tolerance.
  - Quoted cardinalities.
  - Per-spec `temperature` / `num_predict` carry-through.
  - `_messages.flatten` correctness.
- Added 3 new tests in `tests/test_ollama_harness.py`:
  - `temperature` is passed through to Ollama `options`.
  - `num_predict` is passed through.
  - Both are omitted when unset (backwards-compatible behaviour).

**56 tests pass** (up from 44 in Phase 3). All zenodo strategies now
faithfully mirror the upstream `prompt_generation.py` chat-form
construction, and the text-format converter handles every variant we
have observed in `models.csv` / `models_cot.csv` plus common LLM
response quirks.