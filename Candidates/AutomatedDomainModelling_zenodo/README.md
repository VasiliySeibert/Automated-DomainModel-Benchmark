# AutomatedDomainModelling_zenodo

Five prompt strategies from the **Automated Domain Modeling with Large
Language Models: A Comparative Study** artefact, plus two
source-group-shared helpers.

This folder re-uses the prompts and example data from:

> **Chen, K., Yang, Y., Chen, B., Hernández López, J. A., Mussbacher,
> G., & Varró, D.** (2023).
> *Automated Domain Modeling with Large Language Models: A Comparative
> Study.*
> In *2023 ACM/IEEE 26th International Conference on Model Driven
> Engineering Languages and Systems (MODELS)* (pp. 1–11). IEEE.
> DOI: [10.1109/MODELS58315.2023.00012](https://doi.org/10.1109/MODELS58315.2023.00012)
> · IEEE Xplore: https://ieeexplore.ieee.org/document/10344012

The accompanying artefact (code, datasets, evaluation results) is
archived on Zenodo:

> **Chen, K., Yang, Y., Chen, B., Hernández López, J. A., Mussbacher,
> G., & Varró, D.** (2023).
> *Automated Domain Modeling with Large Language Models: A Comparative
> Study* (Version v1) [Data set / supplementary materials]. Zenodo.
> DOI: [10.5281/zenodo.8105098](https://doi.org/10.5281/zenodo.8105098)
> (concept DOI: [10.5281/zenodo.8105097](https://doi.org/10.5281/zenodo.8105097)).
> License: **CC BY 4.0**.

## BibTeX

```bibtex
@inproceedings{chen2023automated,
  author    = {Chen, Kua and Yang, Yujing and Chen, Boqi and
               Hern\'{a}ndez L\'{o}pez, Jos\'{e} Antonio and
               Mussbacher, Gunter and Varr\'{o}, D\'{a}niel},
  title     = {Automated Domain Modeling with Large Language Models:
               A Comparative Study},
  booktitle = {2023 ACM/IEEE 26th International Conference on Model
               Driven Engineering Languages and Systems (MODELS)},
  year      = {2023},
  pages     = {1--11},
  publisher = {IEEE},
  doi       = {10.1109/MODELS58315.2023.00012},
  url       = {https://ieeexplore.ieee.org/document/10344012}
}

@misc{chen_2023_8105098,
  author       = {Chen, Kua and Yang, Yujing and Chen, Boqi and
                  Hern\'{a}ndez L\'{o}pez, Jos\'{e} Antonio and
                  Mussbacher, Gunter and Varr\'{o}, D\'{a}niel},
  title        = {Automated Domain Modeling with Large Language Models:
                  A Comparative Study},
  month        = jul,
  year         = {2023},
  publisher    = {Zenodo},
  version      = {v1},
  doi          = {10.5281/zenodo.8105098},
  url          = {https://doi.org/10.5281/zenodo.8105098},
  note         = {Concept DOI: 10.5281/zenodo.8105097. Supplementary
                  materials (code, data, evaluation) for the MODELS
                  2023 paper. License: CC BY 4.0. Local copy pinned
                  to v1 (LLM\_for\_modelling.zip, md5
                  6f25cd58f1ee9d4e9159bbdd9bcd3c91).}
}
```

## Version pin

| Component | Pin | Source |
|---|---|---|
| Artefact (Zenodo v1) | DOI `10.5281/zenodo.8105098`, 2023-07-01 | https://zenodo.org/records/8105098 |
| `LLM_for_modelling.zip` md5 | `6f25cd58f1ee9d4e9159bbdd9bcd3c91` | Zenodo v1 file metadata |
| Concept DOI (all versions) | `10.5281/zenodo.8105097` | https://zenodo.org/records/8105097 |

The latest artefact version on Zenodo is **v5** (DOI
`10.5281/zenodo.8118642`, 2023-07-06). The local copy used to derive
these prompts corresponds to **v1**; if you need to replicate exact
results, prefer v5.

> **Note**: the upstream artefact is **not** mirrored on GitHub — the
> code is distributed only via the Zenodo zip download.

## Upstream files re-used

| This repo | Upstream |
|---|---|
| `*/prompt_system.txt` | `LLM_for_modelling/llm-model-generation-master/llm-model-generation-master/prompt_generation.py:1` (`PROBLEM_STATEMENT`) |
| `*/prompt_task.txt` | `prompt_generation.py:3-21` (`TASK_DESCRIPTION`) |
| `one_shot_btms/examples.json` | `LLM_for_modelling/.../models.csv` row 2 (BTMS) |
| `one_shot_h2s_short/examples.json` | `LLM_for_modelling/.../models.csv` H2S-Short row |
| `two_shot/examples.json` | BTMS + H2S-Short rows in that order |
| `cot/annotated_example.txt` | `LLM_for_modelling/.../models_cot.csv` H2S row (sentence-by-sentence `->` arrows) |

## Strategies

| Strategy | Upstream config | Skip folders |
|---|---|---|
| `zero_shot` | `generate_prompts_chatgpt` with `shots: []` | — |
| `one_shot_btms` | `generate_prompts_chatgpt` with `shots: ["BTMS"]` | `BTMS` |
| `one_shot_h2s_short` | `generate_prompts_chatgpt` with `shots: ["H2S-Short"]` | `H2S-Short`, `HelpingHands` |
| `two_shot` | `generate_prompts_chatgpt` with `shots: ["BTMS", "H2S-Short"]` | `BTMS`, `H2S-Short`, `HelpingHands` |
| `cot` | `generate_prompts_chatgpt_COT` with `shots: ["H2S"]` (no assistant turn) | `H2S`, `H2S-Short`, `HelpingHands` |

## Group-shared helpers

- **`_messages.py`** — converts an upstream-style
  `[{"role", "content"}, …]` chat-message list to the `(system, user)`
  pair expected by the local Ollama harness, preserving the multi-turn
  structure with `USER:` / `ASSISTANT:` role labels.
- **`zenodo_text_format.py`** — parses the LLM's structured text-format
  response (`Enumeration:` / `Class:` / `Relationships:` sections) into
  a single `@startuml…@enduml` block in the grammar `Data.Parser`
  understands. Tolerant of markdown fences, leading prose, plural
  headings, and `inherit` / `isA` verbs.

## LLM sampling

All 5 zenodo strategies pass `temperature=0.7` and `num_predict=1024`
to the Ollama harness (matches upstream `config.yaml`'s
`running_params` block).

## Dependencies

| Dependency | Version | License | Purpose |
|---|---|---|---|
| Ollama | v0.30.11 | MIT | Local LLM serving |
| spaCy | 3.8.x | MIT | (used by `rule_based`; not by these strategies) |

## Related upstream code

The upstream code calls the OpenAI API directly for the
`gpt-3.5-turbo`, `gpt-4`, `text-davinci-003`, and
`text-chat-davinci-002-20221122` engines used in the original study.
If you wish to reproduce those exact engines, see
[`LLM_for_modelling/.../run_llm.py`][upstream-run-llm] in the Zenodo
zip.

[upstream-run-llm]: https://zenodo.org/records/8105098