# AutomatedDomainModelling_zenodo / cot

A two-stage Chain-of-Thought LLM candidate. Stage 1 uses the H2S
annotated description (with `->` arrows linking each sentence to the
classes / relationships it implies) as the single example, with no
assistant turn — the model is expected to produce its own rationale.
Stage 2 then translates the verbose stage-1 output into a canonical
PlantUML class diagram, and the result is validated line-by-line
before being returned to the benchmark.

## Source

Re-uses the prompt verbatim from:

> **Chen, K., Yang, Y., Chen, B., Hernández López, J. A., Mussbacher,
> G., & Varró, D.** (2023).
> *Automated Domain Modeling with Large Language Models: A Comparative
> Study.* MODELS 2023.
> DOI: [10.1109/MODELS58315.2023.00012](https://doi.org/10.1109/MODELS58315.2023.00012)
> · Zenodo: [10.5281/zenodo.8105098](https://doi.org/10.5281/zenodo.8105098).

`zenodo §5`: `generate_prompts_chatgpt_COT` with `shots=["H2S"]`
(no assistant turn).

## Architecture

The candidate is a small three-stage pipeline:

```
NLT
  │
  ▼
[STAGE 1 LLM]   system=prompt_system.txt
                user=annotated H2S description (with -> arrows)
                user=target NLT
                (no assistant turn — model produces its own rationale)
  │
  ▼
Raw CoT response (likely verbose, with reasoning mixed in)
  │
  ▼
[STAGE 2 LLM]   system=prompt_translate.txt
                user=raw stage-1 output
                temperature 0.0 by default
                (rule 12a specifically targets CoT verbosity:
                 "if your response contains reasoning, ... emit only
                 the final @startuml...@enduml block as your answer")
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
| `candidate.py`        | `CotCandidate` class + module-level `candidate` singleton. Conforms to the `Candidate` Protocol. |
| `run.py`              | Per-candidate driver. Chains `generate.py` → `score.py` → `visualise.py`. |
| `config.json`         | Strategy metadata + model/sampling defaults.                 |
| `metric.json`         | `{"default_metric": "metrik-1"}` — read by `run.py`.         |
| `prompt_system.txt`   | Verbatim zenodo §5 system prompt.                            |
| `prompt_task.txt`     | Verbatim zenodo §5 task description.                         |
| `prompt_translate.txt`| Stage 2 prompt (encodes the metrik-4 grammar explicitly).     |
| `annotated_example.txt` | The H2S annotated description (the CoT example).           |
| `_ollama.py`          | Inlined Ollama `/api/chat` HTTP wrapper, extended with `seed`, `top_p`, `top_k`, `repeat_penalty`, `think` kwargs. |
| `README.md`           | This file.                                                    |

## Skip folders

This strategy is skipped for `H2S`, `H2S-Short`, and `HelpingHands`
records because the H2S annotated description is the only example.
The `generate.py` step honours the `skip_folders` list in `config.json`
automatically.

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

The four cloud tags available via Ollama (`minimax-m3:cloud`, `glm-5.1:cloud`, `kimi-k2.6:cloud`, `nemotron-3-super:cloud`) advertise `thinking` capability. When the prompt is complex or the model decides to think at length, the response is sometimes returned in `message.thinking` rather than `message.content`. The local `_ollama.py` falls back to `thinking` if `content` is empty, but for predictable behaviour set `--no-think` (or pass `think: false` in the Ollama payload) via `OLLAMA_THINK=false`. The `CotCandidate` constructor takes a `think` kwarg (default `False`) for programmatic control.

The non-cloud `qwen2.5-coder:7b` model does not have this quirk.

CoT is the most likely of the four zenodo strategies to surface the
thinking-mode quirk, because the model is asked to reason step-by-step
in stage 1 and the response can be long. The new rule 12a in
`prompt_translate.txt` is specifically designed to handle this: it
tells stage 2 to discard any reasoning text and emit only the final
`@startuml...@enduml` block.

## Usage

```bash
# Full pipeline, kaiser_clean (3 records), default model.
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/cot/run.py \
    --dataset kaiser_clean --limit 3

# Override model + temperature, disable stage 2 translation (A/B mode).
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/cot/run.py \
    --dataset kaiser_clean --limit 3 \
    --model glm-5.1:cloud --temperature 0.7 --no-translate

# Re-run only the visualiser (skip generate + score).
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/cot/run.py \
    --dataset kaiser_clean --skip-generate --skip-score

# Full kaiser_clean with deterministic settings.
PYTHONPATH=. python Candidates/AutomatedDomainModelling_zenodo/cot/run.py \
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

When a record fails, the `error` field in `Workflow/Results/zenodo_cot/_errors.csv` will be one of:

| `error` string                                        | Cause                                                              |
|-------------------------------------------------------|--------------------------------------------------------------------|
| `exception: <class>: <msg>`                           | The Ollama call raised (e.g. `ConnectionError` if Ollama is down). |
| `zenodo_cot_stage1_no_puml`                           | Stage 1 LLM response had no `@startuml…@enduml` block AND could not be parsed as zenodo DSL. |
| `zenodo_cot_stage2_no_puml`                           | Stage 2 LLM response had no `@startuml…@enduml` block.             |
| `zenodo_zero_shot_invalid: <errors>`                  | The validator rejected the final PUML. `<errors>` is a `\|`-joined list of validator findings, truncated to 500 chars. |

## Outputs

Default output folder: `Workflow/Results/zenodo_cot/`.

- `<dataset>.json` — raw generate output.
- `<dataset>_scored.json` — scored.
- `_summary.csv`, `_summary.json` — cross-dataset aggregations.
- `_bucket_<dataset>_<element>_<metric>.csv` — score histograms.
- `_errors.csv` — failure log.
- `heatmap_<dataset>_<element>_<metric>.png` — per-(dataset, element) heatmap.

## Relationship to the other zenodo strategies

This is the last of the four zenodo strategies to be migrated. The
shared `Candidates/AutomatedDomainModelling_zenodo/plantuml_validator.py`
and `_messages.py` modules are reused. The `prompt_translate.txt` file
is a per-strategy copy of the same canonical PUML grammar prompt.

See `Candidates/adjustments.md` for the full migration history.
