# AutomatedDomainModelling_zenodo / one_shot_btms

A two-stage LLM candidate that uses the BTMS example as a one-shot
demonstration, then translates the model's stage-1 output into a
canonical PlantUML class diagram, then validates the result
line-by-line before returning it to the benchmark.

## Source

Re-uses the prompt verbatim from:

> **Chen, K., Yang, Y., Chen, B., Hernández López, J. A., Mussbacher,
> G., & Varró, D.** (2023).
> *Automated Domain Modeling with Large Language Models: A Comparative
> Study.* MODELS 2023.
> DOI: [10.1109/MODELS58315.2023.00012](https://doi.org/10.1109/MODELS58315.2023.00012)
> · Zenodo: [10.5281/zenodo.8105098](https://doi.org/10.5281/zenodo.8105098).

`zenodo §2b`: `generate_prompts_chatgpt` with `shots=["BTMS"]`.

## Architecture

The candidate is a small three-stage pipeline:

```
NLT
  │
  ▼
[STAGE 1 LLM]   system=prompt_system.txt
                user=BTMS description (verbatim from examples.json)
                assistant=BTMS model (verbatim from examples.json)
                user=target NLT
  │
  ▼
Raw model output
  │
  ▼
[STAGE 2 LLM]   system=prompt_translate.txt
                user=raw stage-1 output
                temperature 0.0 by default
  │
  ▼
Final PUML response
  │
  ▼
[VALIDATOR]     plantuml_validator.validate
  │             (auto-repair where mechanical, fail otherwise)
  ▼
Clean PUML  →  CandidateOutput
```

If `--no-translate` is set on `run.py`, the candidate skips stage 2
and validates the intermediate PUML directly. This is the A/B fallback
for measuring the value of the second prompt.

## Files

| File                  | Purpose                                                       |
|-----------------------|---------------------------------------------------------------|
| `candidate.py`        | `OneShotBtmsCandidate` class + module-level `candidate` singleton. Conforms to the `Candidate` Protocol. |
| `run.py`              | Per-candidate driver. Chains `generate.py` → `score.py` → `visualise.py`. |
| `config.json`         | Strategy metadata + model/sampling defaults.                 |
| `metric.json`         | `{"default_metric": "metrik-1"}` — read by `run.py`.         |
| `prompt_system.txt`   | Verbatim zenodo §2b system prompt.                            |
| `prompt_task.txt`     | Verbatim zenodo §2b task description.                         |
| `prompt_translate.txt`| Stage 2 prompt (encodes the metrik-4 grammar explicitly).     |
| `examples.json`       | One entry: BTMS description + BTMS model.                    |
| `_ollama.py`          | Inlined Ollama `/api/chat` HTTP wrapper, extended with `seed`, `top_p`, `top_k`, `repeat_penalty`, `think` kwargs. |
| `README.md`           | This file.                                                    |

## Skip folders

This strategy is skipped for the `BTMS` record because the BTMS
NLT appears verbatim in `examples.json`. The `generate.py` step
honours the `skip_folders` list in `config.json` automatically.

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

The four cloud tags available via Ollama (`minimax-m3:cloud`, `glm-5.1:cloud`, `kimi-k2.6:cloud`, `nemotron-3-super:cloud`) advertise `thinking` capability. When the prompt is complex or the model decides to think at length, the response is sometimes returned in `message.thinking` rather than `message.content`. The local `_ollama.py` falls back to `thinking` if `content` is empty, but for predictable behaviour set `--no-think` (or pass `think: false` in the Ollama payload) via `OLLAMA_THINK=false`. The `OneShotBtmsCandidate` constructor takes a `think` kwarg (default `False`) for programmatic control.

The non-cloud `qwen2.5-coder:7b` model does not have this quirk.

## Usage

```bash
# Full pipeline, kaiser_clean (3 records), default model.
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/one_shot_btms/run.py \
    --dataset kaiser_clean --limit 3

# Override model + temperature, disable stage 2 translation (A/B mode).
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/one_shot_btms/run.py \
    --dataset kaiser_clean --limit 3 \
    --model glm-5.1:cloud --temperature 0.7 --no-translate

# Re-run only the visualiser (skip generate + score).
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/one_shot_btms/run.py \
    --dataset kaiser_clean --skip-generate --skip-score

# Full kaiser_clean with deterministic settings.
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/one_shot_btms/run.py \
    --dataset kaiser_clean --temperature 0.0 --temperature-translate 0.0 --seed 42
```

## CLI flags (in addition to the standard ones)

| Flag                       | Default                          | Effect                                                       |
|----------------------------|----------------------------------|--------------------------------------------------------------|
| `--model TAG`              | `config.json::default_model`     | Ollama model tag. |
| `--temperature FLOAT`      | `0.7`                            | Stage 1 (extraction) temperature.                            |
| `--temperature-translate FLOAT` | `0.0`                        | Stage 2 (translation) temperature. Defaulted to 0.0 for determinism. |
| `--num-predict INT`        | `1024`                           | Max output tokens per LLM call.                              |
| `--seed INT`               | `null`                           | Ollama seed for reproducible outputs.                        |
| `--top-p FLOAT`            | `null`                           | Ollama top_p.                                                |
| `--top-k INT`              | `null`                           | Ollama top_k.                                                |
| `--repeat-penalty FLOAT`   | `null`                           | Ollama repeat_penalty.                                       |
| `--timeout INT`            | `600`                            | Per-call Ollama timeout in seconds.                          |
| `--no-translate`           | translation enabled              | Skip stage 2; validate intermediate PUML directly.           |

## Failure modes

When a record fails, the `error` field in `Workflow/Results/zenodo_one_shot_btms/_errors.csv` will be one of:

| `error` string                                        | Cause                                                              |
|-------------------------------------------------------|--------------------------------------------------------------------|
| `exception: <class>: <msg>`                           | The Ollama call raised (e.g. `ConnectionError` if Ollama is down). |
| `zenodo_one_shot_btms_stage1_no_puml`                 | Stage 1 LLM response had no `@startuml…@enduml` block AND could not be parsed as zenodo DSL. |
| `zenodo_one_shot_btms_stage2_no_puml`                 | Stage 2 LLM response had no `@startuml…@enduml` block.             |
| `zenodo_zero_shot_invalid: <errors>`                  | The validator rejected the final PUML. `<errors>` is a `\|`-joined list of validator findings, truncated to 500 chars. |

## Outputs

Default output folder: `Workflow/Results/zenodo_one_shot_btms/`.

- `<dataset>.json` — raw generate output.
- `<dataset>_scored.json` — scored.
- `_summary.csv`, `_summary.json` — cross-dataset aggregations.
- `_bucket_<dataset>_<element>_<metric>.csv` — score histograms.
- `_errors.csv` — failure log.
- `heatmap_<dataset>_<element>_<metric>.png` — per-(dataset, element) heatmap.

## Relationship to the other zenodo strategies

This is the first of the four one-shot / two-shot / cot zenodo
strategies to be migrated. The shared
`Candidates/AutomatedDomainModelling_zenodo/plantuml_validator.py` and
`_messages.py` modules are reused. The `prompt_translate.txt` file is
a per-strategy copy of the same canonical PUML grammar prompt.

See `Candidates/adjustments.md` for the full migration history.
