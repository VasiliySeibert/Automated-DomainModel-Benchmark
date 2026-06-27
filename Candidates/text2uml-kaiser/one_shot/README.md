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
| `strategy.py`  | Self-contained strategy; imports `Candidates.ollama.harness`. |
| `config.json`  | Discovery metadata.                                           |

## How to run

```bash
PYTHONPATH=. python Workflow/run_full.py \
    --strategies text2uml-kaiser --models glm
```

The orchestrator filters out `AlphaInsurance` from the records passed
to this strategy.