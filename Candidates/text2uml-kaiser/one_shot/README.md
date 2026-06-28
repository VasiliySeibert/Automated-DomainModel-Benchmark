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

```bash
PYTHONPATH=. python Workflow/run_full.py \
    --strategies text2uml-kaiser --models glm
```

The orchestrator filters out `AlphaInsurance` from the records passed
to this strategy.
## Source

Re-uses the prompt verbatim from
[Calamo, Mecella & Snoeck (2025)](https://github.com/IlKaiser/text2uml)
— see [`../README.md`](../README.md) for the full citation block.

