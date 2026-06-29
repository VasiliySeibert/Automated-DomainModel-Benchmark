# text2uml-kaiser / one_shot

Single-call one-shot prompt with **AlphaInsurance** as the verbatim
example (both the NL spec and the reference PlantUML model).

**Skip folder:** `AlphaInsurance` — the model appears verbatim in the
prompt, so it is excluded from the evaluation set.

## Files

| File           | Purpose                                                       |
|----------------|---------------------------------------------------------------|
| `prompt.txt`   | Verbatim copy of `_SHOT_BASE` from upstream.                  |
| `examples.json`| The AlphaInsurance spec + reference UML.                      |
| `strategy.py`  | Self-contained strategy; uses the inlined `_ollama.py` HTTP wrapper. |
| `config.json`  | Discovery metadata.                                           |

## How to run

> **Not yet wired to the new `Candidate` interface.** This strategy's
> `run()` lives in `strategy.py` but has not been wrapped in a
> module-level `candidate` instance yet, and there is no `run.py`
> driver. Once migrated, the invocation pattern will be:
>
> ```bash
> PYTHONPATH=. python Candidates/text2uml-kaiser/one_shot/run.py \
>     --dataset kaiser_clean
> ```
>
> For now the legacy `Workflow/run_full.py` driver referenced in
> earlier revisions has been removed. Track the migration in
> `Candidates/adjustments.md`.

The orchestrator filters out `AlphaInsurance` from the records passed
to this strategy (the migrated driver will do the same).
## Source

Re-uses the prompt verbatim from
[Calamo, Mecella & Snoeck (2025)](https://github.com/IlKaiser/text2uml)
— see [`../README.md`](../README.md) for the full citation block.

