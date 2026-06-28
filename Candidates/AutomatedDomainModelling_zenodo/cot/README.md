# AutomatedDomainModelling_zenodo / cot

One-shot Chain-of-Thought with the **H2S annotated description** as the
single example (zenodo §5). The annotated description shows
sentence-by-sentence `->` arrows linking each sentence to the classes /
relationships it implies — the LLM is expected to produce its own
rationale for the target spec.

**Skip folders:** `H2S`, `H2S-Short`, `HelpingHands`.

## Files

| File                  | Purpose                                       |
|-----------------------|-----------------------------------------------|
| `prompt_system.txt`   | `PROBLEM_STATEMENT`.                          |
| `prompt_task.txt`     | `TASK_DESCRIPTION`.                           |
| `annotated_example.txt` | The H2S annotated description.              |
| `strategy.py`         | Single-call COT strategy; converts to PUML.  |
| `config.json`         | Discovery metadata.                          |

## Source

Re-uses the prompt verbatim from
[Chen, Yang, Chen, Hernández López, Mussbacher & Varró (2023)](https://zenodo.org/records/8105098)
— see [`../README.md`](../README.md) for the full citation block.
