# text2uml-kaiser / cot

5-step Chain-of-Thought. Each step is its own LLM call; the output of
each step feeds into the next step's prompt.

```
spec ──► step1 (class list)
         └► step2 (associations + inheritance)
         └► step2b (attributes)
              └► step3 (cardinalities)
                   └► step5 (PlantUML assembly)
```

If any step produces no usable output, the strategy short-circuits with
`failed=True` and the orchestrator records the failure.

## Files

| File                              | Purpose                                          |
|-----------------------------------|--------------------------------------------------|
| `prompt_step1_class.txt`          | `_COT_CLASS` verbatim.                           |
| `prompt_step2_assoc.txt`          | `_COT_ASSOC` verbatim.                           |
| `prompt_step2b_attr.txt`          | `_COT_ATTR` verbatim.                            |
| `prompt_step3_card.txt`           | `_COT_CARD` verbatim.                            |
| `prompt_step5_plantuml_system.txt`| System prompt enforcing parser-compatible syntax.|
| `prompt_step5_plantuml_user.txt`  | `_COT_PLANT` user template verbatim.              |
| `strategy.py`                     | 5-step chain; imports `Candidates.ollama.harness`. |
| `config.json`                     | Discovery metadata.                              |

## Skip folders

None — no example is used in this strategy.