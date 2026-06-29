# text2uml-kaiser / zero_shot

Single-call direct generation. The LLM is given a system prompt that
describes the PlantUML class-diagram format (with one worked example
for `Book` / `Page`) and the user's natural-language specification.

**No skip folders** — no example model is used in this strategy.

## Files

| File           | Purpose                                              |
|----------------|------------------------------------------------------|
| `prompt.txt`   | Verbatim copy of `_ZERO_SHOT_SYSTEM` from upstream.  |
| `strategy.py`  | Self-contained strategy; uses the inlined `_ollama.py` HTTP wrapper. |
| `config.json`  | Discovery metadata consumed by `Candidates.registry`. |
| `README.md`    | This file.                                            |

## How to run

> **Not yet wired to the new `Candidate` interface.** This strategy's
> `run()` lives in `strategy.py` but has not been wrapped in a
> module-level `candidate` instance yet, and there is no `run.py`
> driver. Once migrated, the invocation pattern will be:
>
> ```bash
> PYTHONPATH=. python Candidates/text2uml-kaiser/zero_shot/run.py \
>     --dataset kaiser_clean
> ```
>
> For now the legacy `Workflow/run_full.py` driver referenced in
> earlier revisions has been removed. Track the migration in
> `Candidates/adjustments.md`.

The strategy's LLM access uses its inlined `_ollama.py` HTTP wrapper
— see [`_ollama.py`](_ollama.py) for the Ollama `/api/chat` schema.

## Source

Re-uses the prompt verbatim from
[Calamo, Mecella & Snoeck (2025)](https://github.com/IlKaiser/text2uml)
— see [`../README.md`](../README.md) for the full citation block.

