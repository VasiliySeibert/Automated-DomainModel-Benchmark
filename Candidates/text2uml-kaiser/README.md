# text2uml-kaiser

Five prompt strategies from the
[Text2UML](https://github.com/IlKaiser/text2uml) project, plus the
shared `Candidates/AutomatedDomainModelling_zenodo/plantuml_validator.py`
for line-by-line PUML validation.

This folder re-uses the prompts and example data from:

> **Calamo, J., Mecella, G., & Snoeck, M.** (2025).
> *Text2UML — a tool for the automated generation of UML class diagrams from natural language text.*

## Strategies

| Strategy | Upstream config | Skip folders |
|---|---|---|
| `zero_shot` | Direct generation, no examples. | — |
| `one_shot` | One example (AlphaInsurance) in the prompt. | `AlphaInsurance` |
| `few_shot` | Two examples (AlphaInsurance + GasStation). | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `cot` | 5-step Chain-of-Thought (class list → associations → attributes → cardinalities → PlantUML). | — |
| `cot_domain` | Domain-aware 5-step CoT (noun list → class list → associations → attributes → PlantUML). | — |

All 5 strategies are LLM-driven and use the same inlined Ollama HTTP
wrapper. They are run through the shared driver
`Candidates/AutomatedDomainModelling_zenodo/run-candidate.py` with
`--strategy kaiser_*`.

## Differences from the zenodo strategies

- **Direct PUML output** (no DSL). The kaiser prompts ask the LLM to
  emit `@startuml...@enduml` directly. There is no stage 1 → stage 2
  translation step. The single LLM call is followed by the
  line-by-line validator.
- **The validator is the key improvement over the legacy `strategy.py`.**
  Today's kaiser pipeline returns whatever PUML block the regex finds,
  which often uses syntax the strict metrik-4 parser doesn't accept
  (e.g. `class Book{ ... }` instead of `class Book { ... }`). The
  validator auto-repairs the common issues and surfaces the rest in
  `_errors.csv`.
- **No 2-stage architecture.** The `enable_translation` and
  `temperature-translate` flags are accepted by the candidate
  classes for uniformity with the zenodo candidates but are no-ops
  for the kaiser strategies.

## Running the benchmark

All 5 kaiser strategies are run through the shared kaiser driver
`Candidates/text2uml-kaiser/run-candidate.py` with
`--strategy kaiser_*`:

```bash
# Smoke test: zero-shot, 3 records, default model.
PYTHONPATH=. OLLAMA_MODEL=glm-5.1:cloud python \
    Candidates/text2uml-kaiser/run-candidate.py \
    --strategy kaiser_zero_shot \
    --dataset kaiser_clean --limit 3

# Full kaiser_clean, deterministic.
PYTHONPATH=. OLLAMA_MODEL=glm-5.1:cloud python \
    Candidates/text2uml-kaiser/run-candidate.py \
    --strategy kaiser_cot --dataset kaiser_clean \
    --temperature 0.0 --seed 42
```

The kaiser driver is self-contained: it does not share code with
the zenodo group driver at `Candidates/AutomatedDomainModelling_zenodo/`.
The two groups have different prompt families, different stage
architectures (kaiser is single-stage, zenodo is two-stage), and
different CLI surface (kaiser has no `--no-translate` or
`--temperature-translate` flags because it has no stage 2).

### Available strategies

| `--strategy` value | Skip folders |
|---|---|
| `kaiser_zero_shot` | — |
| `kaiser_one_shot` | `AlphaInsurance` |
| `kaiser_few_shot` | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `kaiser_cot` | — |
| `kaiser_cot_domain` | — |

### Output folder shape

When `--results-dir` is not set, the driver writes to an
auto-named folder under `Workflow/Results/`:

```
Workflow/Results/<CANDIDATE_ID>_<model_sanitized>_<dataset>_<timestamp>/
```

Identical to the zenodo strategies.

### Visualising across runs

```bash
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py \
    --in 'Workflow/Results/kaiser_*/*_scored.json' \
    --out-dir Workflow/Results/_aggregate/kaiser \
    --metric metrik-4
```

## LLM sampling defaults

All 5 kaiser strategies pass `temperature=0.7` and `num_predict=1024`
to the Ollama harness. These are configurable via the shared
driver's CLI flags (`--temperature`, `--num-predict`, etc.) and via
each strategy's `config.json`.

## Dependencies

| Dependency | Version | License | Purpose |
|---|---|---|---|
| Ollama | v0.30.11 | MIT | Local LLM serving |
| `plantuml_validator` | (shared) | (project) | Line-by-line PUML validation |

## Related upstream code

The kaiser upstream uses different prompt constants for each step
(`_ZERO_SHOT_SYSTEM`, `_ONE_SHOT`, `_FEW_SHOT`, `_COT_*`,
`_DOMAIN_*`). We re-use the prompt text verbatim from
[`text2uml/src/run.py`](https://github.com/IlKaiser/text2uml).

See `Candidates/adjustments.md` for the full migration history.
