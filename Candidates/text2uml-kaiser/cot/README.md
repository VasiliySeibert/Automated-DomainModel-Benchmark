# text2uml-kaiser / cot

A 5-step Chain-of-Thought LLM candidate: class list →
associations+inheritance → attributes → cardinalities →
PlantUML assembly. Each step is its own LLM call. The final
PlantUML is validated line-by-line before being returned to the
benchmark.

## Source

Re-uses the prompts verbatim from
[Calamo, Mecella & Snoeck (2025)](https://github.com/IlKaiser/text2uml)
— see [`../README.md`](../README.md) for the full citation block.

## Architecture

```
NLT
  │
  ▼
[STEP 1 LLM]   prompt_step1_class.txt          → [A, B, C]
  │
  ▼
[STEP 2 LLM]   prompt_step2_assoc.txt         → ASSOCIATIONS: ... INHERITANCE: ...
  │
  ▼
[STEP 2b LLM]  prompt_step2b_attr.txt        → {A: attrs, B: attrs, ...}
  │
  ▼
[STEP 3 LLM]   prompt_step3_card.txt          → A "1" -- "*" B
  │
  ▼
[STEP 5 LLM]   system=prompt_step5_plantuml_system.txt
               user=prompt_step5_plantuml_user.txt
                                              → @startuml...@enduml
  │
  ▼
[VALIDATOR]    plantuml_validator.validate
      │        (auto-repair where mechanical, fail otherwise)
      ▼
Clean PUML  →  CandidateOutput
```

## Files

| File                                | Purpose                                                       |
|-------------------------------------|---------------------------------------------------------------|
| `candidate.py`                      | `KaiserCotCandidate` class + module-level `candidate` singleton. Conforms to the `Candidate` Protocol. |
| `prompt_step1_class.txt`            | Step 1: extract class list.                                   |
| `prompt_step2_assoc.txt`            | Step 2: extract associations + inheritance.                   |
| `prompt_step2b_attr.txt`            | Step 2b: extract attributes.                                  |
| `prompt_step3_card.txt`             | Step 3: assign cardinalities.                                 |
| `prompt_step5_plantuml_system.txt`  | Step 5: PlantUML assembly system prompt.                       |
| `prompt_step5_plantuml_user.txt`    | Step 5: PlantUML assembly user prompt.                         |
| `_ollama.py`                        | Inlined Ollama `/api/chat` HTTP wrapper, extended with `seed`, `top_p`, `top_k`, `repeat_penalty`, `think` kwargs. |
| `config.json`                       | Strategy metadata + model/sampling defaults.                 |
| `metric.json`                       | `{"default_metric": "metrik-1"}` — read by the driver.        |
| `README.md`                         | This file.                                                    |

## Skip folders

None.

## Setup

```bash
# Ollama must be running
ollama serve &

# Default model: qwen2.5-coder:7b (must be pulled first)
ollama pull qwen2.5-coder:7b
```

## Usage

This strategy is run through the shared driver
`Candidates/text2uml-kaiser/run-candidate.py` with
`--strategy kaiser_cot`:

```bash
# Smoke test: 3 records, default model.
PYTHONPATH=. OLLAMA_MODEL=glm-5.1:cloud python \
    Candidates/text2uml-kaiser/run-candidate.py \
    --strategy kaiser_cot \
    --dataset kaiser_clean --limit 3
```

## CLI flags

All sampling flags are accepted by the shared driver. The full
surface is documented in the shared driver's docstring.

## Failure modes

| `error` string                  | Cause                                                              |
|---------------------------------|--------------------------------------------------------------------|
| `exception: <class>: <msg>`     | The Ollama call raised. |
| `cot_step1_no_classes`          | Step 1 LLM response had no parseable class list.                 |
| `cot_step5_no_plantuml`         | Step 5 LLM response had no `@startuml…@enduml` block.            |
| `plantuml_validator: <errors>`  | The validator rejected the final PUML.                            |

CoT is the most fragile of the 5 kaiser strategies: any of the 5
LLM calls can fail, and the chain short-circuits on the first
failure. The legacy kaiser `strategy.py` had the same behaviour;
the migration preserves it.

## Outputs

Default output folder: `Workflow/Results/<strategy>_<model>_<dataset>_<timestamp>/`,
computed by the shared driver.

## Relationship to the other kaiser strategies

All 5 kaiser strategies share the same architecture and the same
shared driver. They differ only in their prompt structure and example
data. See `Candidates/adjustments.md` for the full migration history.
