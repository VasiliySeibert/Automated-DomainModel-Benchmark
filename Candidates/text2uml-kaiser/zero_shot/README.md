# text2uml-kaiser / zero_shot

Single-call direct generation. The LLM is given a system prompt that
describes the PlantUML class-diagram format (with one worked example
for `Book` / `Page`) and the user's natural-language specification.

**No skip folders** — no example model is used in this strategy.

## Files

| File           | Purpose                                              |
|----------------|------------------------------------------------------|
| `prompt.txt`   | Verbatim copy of `_ZERO_SHOT_SYSTEM` from upstream.  |
| `strategy.py`  | Self-contained strategy; imports `Candidates.ollama.harness`. |
| `config.json`  | Discovery metadata consumed by `Candidates.registry`. |
| `README.md`    | This file.                                            |

## How to run

```bash
PYTHONPATH=. python Workflow/run_full.py \
    --strategies text2uml-kaiser --models glm minimax
```

To swap to the opencode harness, edit `strategy.py` and change:
```python
from Candidates.ollama.harness import call as call_llm
```
to
```python
from Candidates.opencode.harness import call as call_llm
```