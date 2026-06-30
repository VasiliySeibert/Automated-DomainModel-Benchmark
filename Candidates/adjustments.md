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

The 5 legacy strategies under `text2uml-kaiser/`
(`zero_shot`, `one_shot`, `few_shot`, `cot`, `cot_domain`) and
`ai4se_benchmarkPaper/rule_based/` (now just `rule_based/` — see the
migrated block below) had their module-level `SPEC = CandidateSpec(...)`
and `register(SPEC)` lines removed. Of these, `rule_based` and the
4 `AutomatedDomainModelling_zenodo/` one-shot / two-shot / cot
strategies have been migrated to the new `Candidate` interface
(see the migrated blocks below). The 5 `text2uml-kaiser/` strategies
remain on the legacy `run(spec, nlt) -> dict` adapter and will be
migrated in a follow-up step.

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

### zenodo_zero_shot — migrated (two-stage with validator)

The LLM-driven `Candidates/AutomatedDomainModelling_zenodo/zero_shot/`
candidate is the first of the 11 legacy LLM strategies to be migrated.
It is also the architectural reference for the other 10 because it
implements the full two-stage pipeline:

- `strategy.py` deleted; its logic inlined into `candidate.py` as
  `TwoStageZeroShotCandidate`.
- New `candidate.py` exposes the module-level `candidate` callable.
  Constructor takes `model`, `temperature`, `temperature_translate`
  (defaults 0.7 / 0.0), `num_predict`, `seed`, `top_p`, `top_k`,
  `repeat_penalty`, `timeout`, `enable_translation`.
- New `metric.json` declares `{"default_metric": "metrik-1"}`.
- New `run.py` is the per-candidate driver with
  `CANDIDATE_ID = "zenodo_zero_shot"`. CLI flags: `--model`,
  `--temperature`, `--temperature-translate`, `--num-predict`,
  `--seed`, `--top-p`, `--top-k`, `--repeat-penalty`, `--timeout`,
  `--no-translate`.
- New `prompt_translate.txt` is the stage 2 LLM prompt. It encodes
  the metrik-4 grammar rules (markers, class declarations, enums,
  four quoted cardinalities, four arrow types `--` / `*--` / `o--` /
  `--|>`, the referenced-class-must-be-declared rule, the
  `_NON_CLASS_TOKENS` blocklist, the identifier regex, no-markdown,
  ordering, output-must-stop-after-`@enduml`). Rule 12a was added
  in a follow-up: "if your response contains reasoning, ... emit
  only the final @startuml...@enduml block as your answer, with no
  other text" — specifically to handle CoT and any other strategy
  that produces multi-paragraph output.
- New shared `Candidates/AutomatedDomainModelling_zenodo/plantuml_validator.py`
  is the line-by-line validator. It auto-repairs mechanical issues
  (add missing class declarations, drop lines with bad endpoints,
  strip markdown fences) and fails the record on non-mechanical
  issues (unrecognised lines, invalid identifiers, missing markers,
  empty diagrams).
- The local `_ollama.py` was extended in place with five new optional
  kwargs (`seed`, `top_p`, `top_k`, `repeat_penalty`, `think`). All
  default to `None` and are omitted from the Ollama `options` block
  if `None`, so the inlined copies in sibling zenodo strategies
  remain functionally identical when called with no extra args. The
  `message.thinking` fallback handles the cloud models that
  occasionally return verbose reasoning in the `thinking` field
  instead of `content`.
- Stage 1 uses the existing zenodo §1b prompt verbatim
  (`prompt_system.txt` + `prompt_task.txt`); stage 2 uses the new
  `prompt_translate.txt`. If `--no-translate` is set, the candidate
  skips stage 2 and validates the intermediate PUML from
  `zenodo_text_format.text_to_plantuml` directly — this is the A/B
  mode for measuring the value of stage 2.

The 9 other legacy LLM strategies from `AutomatedDomainModelling_zenodo/`
(one_shot_btms, one_shot_h2s_short, two_shot, cot, plus 4 under
`text2uml-kaiser/`) remain on the legacy `run(spec, nlt) -> dict`
adapter and will be migrated in subsequent PRs using this candidate
as the template.

### zenodo_one_shot_btms — migrated (one-stage example, two-stage with translation)

The first one-shot LLM strategy to be migrated. Mirrors the
`zenodo_zero_shot — migrated` block in every respect.

- `strategy.py` deleted; new `candidate.py` exposes the module-level
  `candidate` callable wrapping `OneShotBtmsCandidate`.
- Stage 1 message construction follows zenodo §2b:
  `system + user(BTMS nlt) + assistant(BTMS model) + user(target nlt)`.
  The example is read from `examples.json` at module-init time.
- `CANDIDATE_ID = "zenodo_one_shot_btms"`. Skip folder: `BTMS`.
- All 7 sampling flags + `--no-translate` on `run.py`.
- `prompt_translate.txt` is a copy of the canonical PUML grammar
  prompt, kept in sync with the other zenodo strategies (per the
  self-containment decision).
- 3/3 smoke-test records on `kaiser_clean` with `glm-5.1:cloud`,
  `temperature=0.0`, `temperature-translate=0.0`. Generate 16.9 s,
  score 47.9 s, visualise 0.4 s. No failures.

### zenodo_one_shot_h2s_short — migrated (one-stage example, two-stage with translation)

Same shape as `one_shot_btms`, but with the H2S-Short example.

- `OneShotH2sShortCandidate` class. `_build_messages` iterates over
  the single-entry `examples.json` (the H2S-Short example).
- `CANDIDATE_ID = "zenodo_one_shot_h2s_short"`. Skip folders:
  `H2S-Short`, `HelpingHands`.
- 3/3 smoke-test records on `kaiser_clean`. Generate 19.6 s,
  score 57.2 s, visualise 0.4 s. No failures.

### zenodo_two_shot — migrated (two-stage example, two-stage with translation)

Same shape as the one-shots, but `_build_messages` iterates over
**both** examples in `examples.json` (BTMS first, H2S-Short second —
order matters).

- `TwoShotCandidate` class. Shot order is enforced by the order
  in `examples.json`; the candidate does not sort.
- `CANDIDATE_ID = "zenodo_two_shot"`. Skip folders: `BTMS`,
  `H2S-Short`, `HelpingHands`.
- The two-shot prompt is roughly 2× the size of the one-shot
  prompt. With `num_predict=1024` and the cloud models' thinking
  mode off, the response budget is adequate; smoke test
  produced 0 failures on 3 records.
- 3/3 smoke-test records on `kaiser_clean`. Generate 18.8 s,
  score 53.8 s, visualise 0.4 s. No failures.

### zenodo_cot — migrated (no assistant turn, two-stage with translation)

The most distinctive of the four: stage 1 has **no assistant turn**
(zenodo §5). The annotated H2S description is a single user
message, the target NLT is a second user message, and the model
is expected to produce the rationale itself.

- `CotCandidate` class. The annotated H2S description is read from
  `annotated_example.txt` (a single string, not a JSON list of
  `{nlt, model}` pairs).
- `CANDIDATE_ID = "zenodo_cot"`. Skip folders: `H2S`, `H2S-Short`,
  `HelpingHands`.
- CoT is the most verbose of the four strategies. The new rule 12a
  in `prompt_translate.txt` ("if your response contains reasoning,
  emit only the final @startuml...@enduml block as your answer,
  with no other text") specifically targets this. Without 12a the
  stage 2 prompt was receiving analysis prose instead of PUML and
  failing to find an `@startuml` block; with 12a the model produces
  clean output.
- 3/3 smoke-test records on `kaiser_clean`. Generate 27.4 s,
  score 44.0 s, visualise 0.4 s. No failures.

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