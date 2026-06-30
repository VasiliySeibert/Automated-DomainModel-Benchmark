# text2uml-kaiser / zero_shot

A single-call LLM candidate that asks the model to produce a
PlantUML class diagram directly from a natural-language specification
(no examples, no intermediate DSL). The LLM's raw output is then
validated line-by-line before being returned to the benchmark.

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
        user="Transform into plant uml this specification text: {nlt}"
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

The validator is the key improvement over the legacy `strategy.py`:
today's kaiser pipeline returns whatever PUML block the regex finds,
which often uses syntax the strict metrik-4 parser doesn't accept
(e.g. `class Book{ ... }` instead of `class Book { ... }`). The
validator auto-repairs the common issues and surfaces the rest in
`_errors.csv`.

## Files

| File                  | Purpose                                                       |
|-----------------------|---------------------------------------------------------------|
| `candidate.py`        | `KaiserZeroShotCandidate` class + module-level `candidate` singleton. Conforms to the `Candidate` Protocol. |
| `prompt.txt`          | Verbatim copy of `_ZERO_SHOT_SYSTEM` from upstream.            |
| `_ollama.py`          | Inlined Ollama `/api/chat` HTTP wrapper, extended with `seed`, `top_p`, `top_k`, `repeat_penalty`, `think` kwargs. |
| `config.json`         | Strategy metadata + model/sampling defaults.                 |
| `metric.json`         | `{"default_metric": "metrik-1"}` — read by the driver.        |
| `README.md`           | This file.                                                    |

## Skip folders

None — no example model is used in this strategy.

## Setup

```bash
# Ollama must be running
ollama serve &

# Default model: qwen2.5-coder:7b (must be pulled first)
ollama pull qwen2.5-coder:7b

# Alternatively, use one of the pre-installed cloud tags:
#   minimax-m3:cloud
#   glm-5.1:cloud
#   kimi-k2.6:cloud
#   nemotron-3-super:cloud
# (pass via --model or set OLLAMA_MODEL)
```

## Thinking-mode quirk

The four cloud tags available via Ollama advertise `thinking`
capability. When the prompt is complex or the model decides to think
at length, the response is sometimes returned in `message.thinking`
rather than `message.content`. The local `_ollama.py` falls back to
`thinking` if `content` is empty. For predictable behaviour, set
`think=False` (the default) in the candidate's `__init__`. The
`KaiserZeroShotCandidate` constructor takes a `think` kwarg
(default `False`) for programmatic control.

The non-cloud `qwen2.5-coder:7b` model does not have this quirk.

## Usage

This strategy is run through the shared driver
`Candidates/text2uml-kaiser/run-candidate.py` with
`--strategy kaiser_zero_shot`:

```bash
# Smoke test: 3 records, default model.
PYTHONPATH=. OLLAMA_MODEL=glm-5.1:cloud python \
    Candidates/text2uml-kaiser/run-candidate.py \
    --strategy kaiser_zero_shot \
    --dataset kaiser_clean --limit 3

# Full kaiser_clean, deterministic settings.
PYTHONPATH=. OLLAMA_MODEL=glm-5.1:cloud python \
    Candidates/text2uml-kaiser/run-candidate.py \
    --strategy kaiser_zero_shot --dataset kaiser_clean \
    --temperature 0.0 --seed 42
```

## CLI flags

All sampling flags are accepted by the shared driver. The full
surface is documented in the shared driver's docstring.

## Failure modes

When a record fails, the `error` field in the auto-named output
folder's `_errors.csv` will be one of:

| `error` string                                        | Cause                                                              |
|-------------------------------------------------------|--------------------------------------------------------------------|
| `exception: <class>: <msg>`                           | The Ollama call raised (e.g. `ConnectionError` if Ollama is down). |
| `kaiser_zero_shot_no_plantuml`                       | Stage 1 LLM response had no `@startuml…@enduml` block.             |
| `plantuml_validator: <errors>`                        | The validator rejected the final PUML. `<errors>` is a `\|`-joined list of validator findings, truncated to 500 chars. |

## Outputs

Default output folder: `Workflow/Results/<strategy>_<model>_<dataset>_<timestamp>/`,
computed by the shared driver.

- `<dataset>.json` — raw generate output.
- `<dataset>_scored.json` — scored.
- `_summary.csv`, `_summary.json` — cross-dataset aggregations.
- `_bucket_<dataset>_<element>_<metric>.csv` — score histograms.
- `_errors.csv` — failure log.
- `heatmap_<dataset>_<element>_<metric>.png` — per-(dataset, element) heatmap.

## Relationship to the other kaiser strategies

All 5 kaiser strategies (`kaiser_zero_shot`, `kaiser_one_shot`,
`kaiser_few_shot`, `kaiser_cot`, `kaiser_cot_domain`) share the
same architecture and the same shared driver
`Candidates/text2uml-kaiser/run-candidate.py`. They
differ only in their prompt structure and example data.

See `Candidates/adjustments.md` for the full migration history.
