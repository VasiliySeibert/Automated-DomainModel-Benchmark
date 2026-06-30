# text2uml-kaiser / few_shot

A single-call LLM candidate that uses the kaiser `_PROMPT_FEW_SHOT`
template: a base system prompt plus two worked examples
(AlphaInsurance + GasStation) plus the target NLT, separated by
`##############` blocks. The LLM's raw output is validated
line-by-line before being returned to the benchmark.

## Source

Re-uses the prompt verbatim from
[Calamo, Mecella & Snoeck (2025)](https://github.com/IlKaiser/text2uml)
— see [`../README.md`](../README.md) for the full citation block.

## Architecture

```
NLT
  │
  ▼
[LLM]   system=prompt.txt
        user=base + 2 examples + new spec (############## block format)
  │
  ▼
Raw PlantUML response
  │
  ▼
[VALIDATOR]     plantuml_validator.validate
  │             (auto-repair where mechanical, fail otherwise)
  ▼
Clean PUML  →  CandidateOutput
```

## Files

| File                  | Purpose                                                       |
|-----------------------|---------------------------------------------------------------|
| `candidate.py`        | `KaiserFewShotCandidate` class + module-level `candidate` singleton. Conforms to the `Candidate` Protocol. |
| `prompt.txt`          | Verbatim copy of the kaiser shot-base header.                 |
| `examples.json`       | Two entries: AlphaInsurance + GasStation.                    |
| `_ollama.py`          | Inlined Ollama `/api/chat` HTTP wrapper, extended with `seed`, `top_p`, `top_k`, `repeat_penalty`, `think` kwargs. |
| `config.json`         | Strategy metadata + model/sampling defaults.                 |
| `metric.json`         | `{"default_metric": "metrik-1"}` — read by the driver.        |
| `README.md`           | This file.                                                    |

## Skip folders

`AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` — the two examples
appear verbatim in `examples.json` and are excluded from the
evaluation set (the second is a single record that appears as
`GasStation` in the kaiser upstream; we skip both `_KUL` and `_TUW`
suffixes for safety).

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
`--strategy kaiser_few_shot`:

```bash
# Smoke test: 3 records, default model.
PYTHONPATH=. OLLAMA_MODEL=glm-5.1:cloud python \
    Candidates/text2uml-kaiser/run-candidate.py \
    --strategy kaiser_few_shot \
    --dataset kaiser_clean --limit 3
```

## CLI flags

All sampling flags are accepted by the shared driver. The full
surface is documented in the shared driver's docstring.

## Failure modes

| `error` string                                        | Cause                                                              |
|-------------------------------------------------------|--------------------------------------------------------------------|
| `exception: <class>: <msg>`                           | The Ollama call raised. |
| `kaiser_few_shot_no_plantuml`                        | Stage 1 LLM response had no `@startuml…@enduml` block.             |
| `plantuml_validator: <errors>`                        | The validator rejected the final PUML.                            |

## Outputs

Default output folder: `Workflow/Results/<strategy>_<model>_<dataset>_<timestamp>/`,
computed by the shared driver.

## Relationship to the other kaiser strategies

All 5 kaiser strategies share the same architecture and the same
shared driver. They differ only in their prompt structure and example
data. See `Candidates/adjustments.md` for the full migration history.
