# text2uml-kaiser strategies

Five strategies from Kaiser 2026 (`text2uml-kaiser/src/run.py`).
All strategies are **fully self-contained** — each has its own
folder with `strategy.py`, `prompt*.txt`, and `config.json`.

| Strategy       | Skip folders                              |
|----------------|-------------------------------------------|
| `zero_shot`    | —                                         |
| `one_shot`     | `AlphaInsurance`                          |
| `few_shot`     | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `cot`          | —                                         |
| `cot_domain`   | —                                         |

## Harness

All strategies import `Candidates.ollama.harness`. To switch to
`opencode`, change one import line in each `strategy.py`.

## Cell count

5 strategies × 4 models × 2 datasets = **40 cells** (with skip rules
applied: 36 cells on kaiser, 4 cells on reference).

## Reused verbatim

- `_ZERO_SHOT_SYSTEM` (run.py:51-86) → `zero_shot/prompt.txt`
- `_SHOT_BASE` (run.py:94-129) → `one_shot/prompt.txt`, `few_shot/prompt.txt`
- `_INSURANCE_SPEC`, `_INSURANCE_UML` → `one_shot/examples.json`, `few_shot/examples.json`
- `_GASSTATION_SPEC`, `_GASSTATION_UML` → `few_shot/examples.json`
- `_COT_*` (5 prompts) → `cot/prompt_step{1,2,2b,3,5}_*.txt`
- `_DOMAIN_*` (5 prompts) → `cot_domain/prompt_step{1,2,3,2b,5}_*.txt`

The double-brace `{{ }}` syntax in the upstream LangChain templates has
been collapsed to single braces in the copied prompt files (LLMs need
valid PlantUML).