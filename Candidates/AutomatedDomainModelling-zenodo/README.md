# AutomatedDomainModelling-zenodo strategies

Five strategies from Bademoses 2024
(`AutomatedDomainModelling-zenodo/prompts.md` +
`LLM_for_modelling/llm-model-generation-master/prompt_generation.py`).
All strategies are **fully self-contained** — each has its own folder
with `strategy.py`, `prompt*.txt`, `examples.json` / `annotated_example.txt`,
and `config.json`.

| Strategy            | Skip folders                                |
|---------------------|---------------------------------------------|
| `zero_shot`         | —                                           |
| `one_shot_btms`     | `BTMS`                                      |
| `one_shot_h2s_short`| `H2S-Short`, `HelpingHands`                 |
| `two_shot`          | `BTMS`, `H2S-Short`, `HelpingHands`         |
| `cot`               | `H2S`, `H2S-Short`, `HelpingHands`          |

## Harness

All strategies import `Candidates.ollama.harness`. To switch to
`opencode`, change one import line in each `strategy.py`.

## Cell count

5 strategies × 4 models × 2 datasets = **40 cells** (with skip rules
applied).

## Source-group-shared helper

`zenodo_text_format.py` (in this folder) is the text-to-PlantUML
converter. It is **only** imported by the zenodo strategies; no other
group uses it. The folder structure is otherwise fully self-contained.

## Reused verbatim

- `PROBLEM_STATEMENT` (`prompt_generation.py:1`) → `*/prompt_system.txt`
- `TASK_DESCRIPTION` (`prompt_generation.py:3-21`) → `*/prompt_task.txt`
- `BTMS` row from `models.csv` → `one_shot_btms/examples.json`,
  `two_shot/examples.json`
- `H2S-Short` row from `models.csv` → `one_shot_h2s_short/examples.json`,
  `two_shot/examples.json`
- H2S annotated description (`models_cot.csv` H2S row) →
  `cot/annotated_example.txt`