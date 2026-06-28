# text2uml-kaiser

Five prompt strategies from:

> **Calamo, M., Mecella, M., & Snoeck, M.** (2025).
> *Assessing the Suitability of Large Language Models in Generating UML
> Class Diagrams as Conceptual Models.*
> In *International Conference on Business Process Modeling, Development
> and Support* (pp. 211–226). Springer.

The companion dataset and aggregated results are published as:

> **Calamo, M., Mecella, M., & Snoeck, M.** (2026).
> *Text2UML results with Golden UML Dataset* (Version v1) [Data set].
> Zenodo.
> DOI: [10.5281/zenodo.19599470](https://doi.org/10.5281/zenodo.19599470)
> (concept DOI: [10.5281/zenodo.19599469](https://doi.org/10.5281/zenodo.19599469)).
> License: **CC BY 4.0**.

The companion source code is on GitHub:

> **IlKaiser/text2uml** — Calamo, Mecella & Snoeck (2025).
> GitHub. https://github.com/IlKaiser/text2uml.
> License: **GPL-3.0**.

## BibTeX

```bibtex
@inproceedings{calamo2025assessing,
  author    = {Calamo, Marco and Mecella, Massimo and Snoeck, Monique},
  title     = {Assessing the Suitability of Large Language Models
               in Generating {UML} Class Diagrams as Conceptual Models},
  booktitle = {International Conference on Business Process Modeling,
               Development and Support},
  pages     = {211--226},
  year      = {2025},
  publisher = {Springer}
}

@dataset{calamo_2026_19599470,
  author    = {Calamo, Marco and Mecella, Massimo and Snoeck, Monique},
  title     = {Text2UML results with Golden UML Dataset},
  month     = apr,
  year      = {2026},
  publisher = {Zenodo},
  version   = {v1},
  doi       = {10.5281/zenodo.19599470},
  url       = {https://doi.org/10.5281/zenodo.19599470}
}
```

## Version pin

| Component | Pin | Source |
|---|---|---|
| Dataset (Zenodo v1) | DOI `10.5281/zenodo.19599470`, 2026-04-15 | https://zenodo.org/records/19599470 |
| Code (`IlKaiser/text2uml`) | commit `c50aa8a9b652e0d02232170bfe397ea6e380307e` on `main`, 2026-06-26 | https://github.com/IlKaiser/text2uml/tree/c50aa8a9b652e0d02232170bfe397ea6e380307e |

> Note: the git commit above post-dates the v1 Zenodo deposit; for exact
> replication of the published results, use the parent commit on `main`
> from 2026-04-15 or earlier.

## Strategies

| Strategy | Upstream builder | Skip folders |
|---|---|---|
| `zero_shot` | `_ZERO_SHOT_SYSTEM` + `Transform into plant uml …` user prompt | — |
| `one_shot` | `_SHOT_BASE` + AlphaInsurance example | `AlphaInsurance` |
| `few_shot` | `_SHOT_BASE` + AlphaInsurance + GasStation examples | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `cot` | 5-step chain: class list → associations+inheritance → attributes → cardinalities → PlantUML | — |
| `cot_domain` | 5-step domain-aware chain: nouns → classes → associations → attributes → PlantUML | — |

## Verbatim re-use vs. adaptations

| This repo | Upstream (`text2uml-kaiser/src/run.py`) | Match |
|---|---|---|
| `zero_shot/prompt.txt` | `_ZERO_SHOT_SYSTEM` (line 51) | **exact** |
| `one_shot/prompt.txt`, `few_shot/prompt.txt` | `_SHOT_BASE` (line 94) | **exact** |
| `one_shot/examples.json[*].nlt`, `few_shot/examples.json[*].nlt` | `_INSURANCE_SPEC` (line 131), `_GASSTATION_SPEC` (line 204) | **exact** |
| `few_shot/examples.json[GasStation].model` | `_GASSTATION_UML` (line 232) | **exact** |
| `one_shot/examples.json[0].model` | `_INSURANCE_UML` (line 155) | trimmed (drops `Double calculateCompenstationSum()` method and `(ClaimCase,Estimator) .. Report` association-class line) |
| `cot/prompt_step{1,2,3}_*.txt`, `cot_domain/prompt_step{1,2,3}_*.txt` | `_COT_*` / `_DOMAIN_*` | cosmetic only (`{text}` → `{nlt}` placeholder rename, `{{...}}` → `{...}` brace-collapse) |
| `cot/prompt_step5_plantuml_system.txt`, `cot_domain/prompt_step5_plantuml_system.txt` | `_COT_PLANT` / `_DOMAIN_PLANT` | **rewritten** — stricter syntax (parser-compatible) |

## Harness

All strategies use their own inlined `_ollama.py` HTTP wrapper — see
[`zero_shot/_ollama.py`](zero_shot/_ollama.py) for the canonical copy.
The other 4 strategies' `_ollama.py` are byte-identical copies
(enforced by `tests/test_ollama_inlined.py`).

To swap to a different LLM backend, replace `_ollama.py` in the
strategy folder with a module exposing `call(model, system, prompt, *, timeout, temperature=None, num_predict=None) -> str`.

## Cell count

5 strategies × 4 models × 2 datasets = **40 cells** (with skip rules
applied: 36 cells on kaiser, 4 cells on reference).

## Dependencies

| Dependency | Version | License | Purpose |
|---|---|---|---|
| Ollama | v0.30.11 | MIT | Local LLM serving |
| LangChain (upstream only) | 0.3.27 | MIT | Prompt template machinery (upstream; not used here) |
| spaCy (upstream `text/` only) | 3.8.x | MIT | Linguistic complexity metrics (upstream; not used here) |