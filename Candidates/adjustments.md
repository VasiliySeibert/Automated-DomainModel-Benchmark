# Prompt & Logic Adjustments vs. Source Repositories

Each prompt strategy in this benchmark reuses the **verbatim text** from one
of three pre-existing prompt suites:

1. **`text2uml-kaiser/src/run.py`** (Kaiser 2026) — zero-shot, one-shot,
   few-shot, CoT, CoT-domain prompts.
2. **`AutomatedDomainModelling-zenodo/prompts.md`** (Bademoses 2024) +
   `LLM_for_modelling/llm-model-generation-master/prompt_generation.py` —
   zero-shot (text format), one-shot BTMS, one-shot H2S-Short, two-shot,
   CoT (H2S annotated).
3. **`ai4se_benchmarkPaper/benchmark/candidates/rule_based/utils.py`** —
   spaCy-based SVO + verb-lemma heuristic.

## 1. Fully self-contained candidates

Per the user's explicit requirement, **every candidate folder contains
everything it needs** — `strategy.py`, `prompt*.txt`, `examples.json`,
`config.json`, `README.md`. There is no global `base.py`, no shared
`Strategy` class, no shared plan / execute modules.

Each strategy imports **one harness** at the top of `strategy.py`:
```python
from Candidates.ollama.harness import call as call_llm
```
Swapping to the `opencode` harness is a one-line edit per strategy.

## 2. The two harnesses

| Folder              | Type          | Default | Endpoint                                |
|---------------------|---------------|---------|-----------------------------------------|
| `Candidates/ollama/`     | HTTP wrapper  | ✓       | `POST $OLLAMA_HOST/api/chat` (default `http://localhost:11434`) |
| `Candidates/opencode/`   | subprocess    | ✗       | `opencode run --model <id>`            |

The ollama harness is 2-3× faster than opencode for the same model
(no subprocess overhead, no "system prompt" CLI-flag workaround). The
opencode harness exists as a candidate for completeness — it can be
swapped in per-strategy if desired.

## 3. Discovery via `Candidates/registry.py`

The registry walks the tree:

```
Candidates/
├── ollama/                  # harness, NOT a strategy
├── opencode/                # harness, NOT a strategy
├── text2uml-kaiser/         # SOURCE GROUP
│   └── <strategy>/strategy.py
├── AutomatedDomainModelling_zenodo/   # SOURCE GROUP
│   └── <strategy>/strategy.py
└── ai4se_benchmarkPaper/    # SOURCE GROUP
    └── rule_based/strategy.py
```

Each `strategy.py` declares a `SPEC = CandidateSpec(...)` at module
level and calls `register(SPEC)`. The dynamic import machinery in
`_import_module` uses `importlib.util.spec_from_file_location` for
defensive isolation; all source-group folder names use underscores so
they are importable as normal Python packages (e.g.
`Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format`).

`SOURCE_DIRS` enumerates the three source groups; strategies outside
these directories (the two harnesses) are excluded.

## 4. Cell matrix

| Source                            | Strategies | × Models | Cells/dataset | × 2 datasets | Records |
|-----------------------------------|-----------:|---------:|---------------:|-------------:|--------:|
| `text2uml-kaiser/`                |          5 |        4 |             20 |           40 |      40 |
| `AutomatedDomainModelling_zenodo/`|       5 |        4 |             20 |           40 |      40 |
| `ai4se_benchmarkPaper/rule_based/`|      1 |        1 |              1 |            2 |       2 |
| **TOTAL**                         |     **11** |          |          **41** |       **82** |  **82** |

## 5. Kaiser strategies — verified inventory

Re-audited against `text2uml-kaiser/src/run.py` via two `@explore` agents.
The five-strategy inventory (`zero_shot`, `one_shot`, `few_shot`, `cot`,
`cot_domain`) is **complete** — no other strategies are defined in the
upstream `_CHAIN_BUILDERS` registry (lines 884-890), the
`techniques:` block of `config.yaml` (lines 14-31), or any other file in
the upstream repo.

Verbatim text reuse:

| This repo                                        | Upstream                                          |
|--------------------------------------------------|---------------------------------------------------|
| `text2uml-kaiser/zero_shot/prompt.txt`           | `_ZERO_SHOT_SYSTEM` (run.py:51-86)                |
| `text2uml-kaiser/one_shot/prompt.txt`            | `_SHOT_BASE` (run.py:94-129)                      |
| `text2uml-kaiser/one_shot/examples.json`         | `_INSURANCE_SPEC` + `_INSURANCE_UML` (run.py:131-202)|
| `text2uml-kaiser/few_shot/examples.json`         | + `_GASSTATION_SPEC` + `_GASSTATION_UML` (run.py:204-269) |
| `text2uml-kaiser/cot/prompt_step{1,2,2b,3,5}_*.txt` | `_COT_CLASS` / `_COT_ASSOC` / `_COT_ATTR` / `_COT_CARD` / `_COT_PLANT` (run.py:336-550) |
| `text2uml-kaiser/cot_domain/prompt_step{1,2,3,2b,5}_*.txt` | `_DOMAIN_NOUN` / `_DOMAIN_CLASS` / `_DOMAIN_ASSOC` / `_COT_ATTR` (reused) / `_DOMAIN_PLANT` (run.py:553-746) |

Brace fixup: every `{{` → `{` and `}}` → `}` in the upstream prompts
(LangChain's brace-escape syntax) has been collapsed to single braces
in the per-strategy prompt files. The LLM sees valid PlantUML.

## 6. Zenodo strategies — verified inventory

Re-audited against `AutomatedDomainModelling-zenodo/prompts.md` and
the source code in `LLM_for_modelling/llm-model-generation-master/
prompt_generation.py`. The five-setting inventory (`zero_shot`,
`one_shot_btms`, `one_shot_h2s_short`, `two_shot`, `cot`) is
**complete** — confirmed by:

- 5 entries in `Round 1 Evaluation/first_round.csv` Setting column.
- 5 entries in `Round 2 Evaluation/second_round.csv` Setting column.
- 5 × 3 = 15 saved result XLSX files in `experiments_result/`.

**Chat-form fidelity.** The ollama harness exposes only one `system`
slot plus one `user` slot per call, so the upstream multi-turn chat
list (built by `generate_prompts_chatgpt` / `generate_prompts_chatgpt_COT`)
is flattened via the source-group-shared helper
`AutomatedDomainModelling_zenodo/_messages.py`: the system message
goes to the harness `system=` argument; the remaining turns are
concatenated into the user prompt with `USER:` / `ASSISTANT:` role
labels so the multi-turn structure is preserved.

Verbatim text reuse:

| This repo                                        | Upstream                                          |
|--------------------------------------------------|---------------------------------------------------|
| `*/prompt_system.txt`                            | `PROBLEM_STATEMENT` (prompt_generation.py:1)     |
| `*/prompt_task.txt`                              | `TASK_DESCRIPTION` (prompt_generation.py:3-21)    |
| `one_shot_btms/examples.json`                    | `models.csv` BTMS row                             |
| `one_shot_h2s_short/examples.json`               | `models.csv` H2S-Short row                        |
| `two_shot/examples.json`                         | BTMS + H2S-Short rows                             |
| `cot/annotated_example.txt`                      | `models_cot.csv` H2S row (sentence-by-sentence `->` arrows) |

**Upstream sampling defaults.** All 5 zenodo strategies pass
`temperature=0.7` and `num_predict=1024` to the ollama harness (from
upstream `config.yaml` running_params block), set as `CandidateSpec`
fields so the registry carries them.

## 7. Zenodo text format → PlantUML conversion

The zenodo prompts ask the LLM to emit a structured text response of
the form `Enumeration:` / `Class:` / `Relationships:` sections — not
valid PlantUML. We convert via the source-group-shared helper
`AutomatedDomainModelling_zenodo/zenodo_text_format.py` (only imported
by the zenodo strategies; no other group uses it). The converter
parses the text and emits a single `@startuml…@enduml` block in the
parser-compatible grammar.

If the LLM ignores the format and emits PlantUML directly, the
strategy extracts the block with `extract_plantuml_block` and skips
the conversion.

**Converter tolerance:**
- `Enumeration` / `Enumerations` / `Class` / `Classes` /
  `Relationship` / `Relationships` headings (case-insensitive,
  with or without trailing colon).
- `inherit` *and* `isA` verbs (the CoT annotated H2S example uses both).
- Markdown code fences (` ``` … ``` `) wrapping the response.
- Leading prose before the first heading.
- Cardinalities are emitted quoted (`Source "1" -- "*" Target`) —
  the parser accepts both quoted and unquoted, but quoted matches
  the kaiser step-5 convention.

## 8. Cardinality quoting

PlantUML accepts both `A "1" -- "*" B` (quoted) and `A 1 -- * B`
(unquoted). The parser handles both, but the LLM occasionally emits
`n-m` (hyphen) which is invalid. The execute prompt restricts to
`"1"`, `"*"`, `"0..*"`, `"1..*"`, `"0..1"`, `"n..m"` (hyphen forbidden).

## 9. Skip rules

| Strategy                                    | Skipped folders                                       |
|---------------------------------------------|------------------------------------------------------|
| `text2uml-kaiser/one_shot`                 | `AlphaInsurance`                                      |
| `text2uml-kaiser/few_shot`                 | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `AutomatedDomainModelling_zenodo/one_shot_btms` | `BTMS`                                           |
| `AutomatedDomainModelling_zenodo/one_shot_h2s_short` | `H2S-Short`, `HelpingHands`                  |
| `AutomatedDomainModelling_zenodo/two_shot`  | `BTMS`, `H2S-Short`, `HelpingHands`                   |
| `AutomatedDomainModelling_zenodo/cot`       | `H2S`, `H2S-Short`, `HelpingHands`                   |
| `rule_based`                                | —                                                    |
| `text2uml-kaiser/{zero_shot,cot,cot_domain}` | —                                                    |
| `AutomatedDomainModelling-zenodo/zero_shot` | —                                                    |

## 10. Failure handling

**No retries.** `Strategy.run()` returns `StrategyResult(error=...)`
on any failure. The orchestrator catches all exceptions, records
`failed=True` + `error`, and proceeds. Failed records appear in
`_errors.csv` with `{source, strategy, model, dataset, id, error,
raw_excerpt}` (200-char excerpt of the LLM's raw output for debugging).

## 11. Bucket boundaries for the result tables

`Workflow/Results/_bucket_<dataset>_<element>.csv` (one per dataset
× element = 6 files). Score buckets:
`[0, 0.1) / [0.1, 0.2) / [0.2, 0.3) / [0.3, 1.0]`.

The `[0.3, 1.0]` bucket captures "anything metrik-4 considers
substantive" — this aligns with the 0.71 cap observed for identical
inputs in the kaiser/reference corpora. The three low buckets resolve
the spread within the "mediocre" range.

## 12. Authentication / runtime assumptions

- `ollama list` shows `minimax-m3:cloud`, `kimi-k2.6:cloud` are
  pre-pulled. The other two (`glm-5.1`, `nemotron-3-super`) are NOT
  pre-pulled — `ollama run` will fetch them on first use. The
  `--smoke` mode only invokes `rule_based` to avoid the cold-start
  penalty.
- Each LLM call takes ~30-60s on cloud Ollama. The full run
  (8 strategies × 4 models × 2 datasets × ~26 records average) is
  estimated at **30-90 minutes**.