# rule_based — re-implementation of Abdelnabi et al. (2020)

Non-LLM baseline candidate. Extracts OO concepts (classes, attributes,
relationships) from natural-language requirements using NLP techniques
and hand-tuned heuristic rules — **no LLM call**. Acts as a
non-LLM baseline for the benchmark.

## Source — Abdelnabi et al. (2020)

This candidate is a re-implementation of the algorithm described in:

> **Abdelnabi, E. A., Maatuk, A. M., Abdelaziz, T. M., & Elakeili,
> S. M.** (2020).
> *Generating UML Class Diagram using NLP Techniques and Heuristic
> Rules.*
> In *2020 20th International Conference on Sciences and Techniques
> of Automatic Control and Computer Engineering (STA)* (pp. 277–282).
> IEEE.
> DOI: [10.1109/STA50679.2020.9329301](https://doi.org/10.1109/STA50679.2020.9329301)
> · IEEE Xplore: https://ieeexplore.ieee.org/document/9329301

The paper proposes a method for generating class diagrams from software
requirements specifications using NL practices plus a set of heuristic
rules. The pre-defined rules extract OO concepts (classes, attributes,
methods, relationships) from the formalised token stream.

### BibTeX

```bibtex
@inproceedings{abdelnabi2020generating,
  author    = {Abdelnabi, Esra A. and Maatuk, Abdelsalam M. and
               Abdelaziz, Tawfig M. and Elakeili, Salwa M.},
  title     = {Generating {UML} Class Diagram using {NLP} Techniques
               and Heuristic Rules},
  booktitle = {2020 20th International Conference on Sciences and
               Techniques of Automatic Control and Computer Engineering
               (STA)},
  year      = {2020},
  pages     = {277--282},
  publisher = {IEEE},
  address   = {Monastir, Tunisia},
  doi       = {10.1109/STA50679.2020.9329301},
  url       = {https://ieeexplore.ieee.org/document/9329301}
}
```

### APA 7

Abdelnabi, E. A., Maatuk, A. M., Abdelaziz, T. M., & Elakeili, S. M.
(2020). Generating UML class diagram using NLP techniques and heuristic
rules. In *2020 20th International Conference on Sciences and Techniques
of Automatic Control and Computer Engineering (STA)* (pp. 277–282).
IEEE. https://doi.org/10.1109/STA50679.2020.9329301

## How the re-implementation differs from the paper

The paper's original algorithm is a **flat NLP pipeline**:
tokenisation → POS-tagging → removal of "to-be" and modal verbs →
flat regex-style heuristic patterns over the cleaned token list.

This re-implementation preserves the spirit of the paper but uses
**spaCy dependency parsing** instead of the flat pipeline, which gives
richer per-verb context (subjects, objects, prepositional phrases,
conjuncts) without explicit "to-be" removal. Concretely:

- spaCy `en_core_web_sm` provides tokenisation, POS tagging, lemmatisation,
  and a full dependency parse in one pass.
- **Class extraction:** all tokens with `pos_ ∈ {NOUN, PROPN}` plus
  subjects/objects from the SVO parse.
- **Relationship extraction:** five dedicated extractors driven by
  hand-curated verb-lemma lexicons:
  - **association** — verbs `{take, send, buy, give, show, record,
    work, talk}` → `--`
  - **aggregation** — verbs `{hold, carry, involve, imply, embrace,
    consist, comprise, belong, divide, include}` → `o--` with
    per-verb preposition handling (`consist of`, `belong to`,
    `include in`, …)
  - **composition** — verbs `{have, comprise, possess, contain}` →
    `*--` with reversed direction
  - **include** — special-case handler for the verb `include` with
    reversed direction
  - **generalization** — copular `be` (lemma) with `attr/acomp` or
    `prep "of" + pobj`; direction reversed on `maybe` or auxiliary
    `can`
- **Cardinality inference:** plural `NNS/NNPS` → `"1..*"`, else `"1"`.
- **Parser-compliance sanitiser:** two layers of defence against
  emitting PUML that the strict metrik-4 parser (and metrik-1..3, 5,
  all of which run their parser in `strict=True` mode) would reject:
  1. `heuristic.py::c_rule_extract_classes` filters NOUN/PROPN tokens
     whose text is not a valid PlantUML identifier (`[A-Za-z_][A-Za-z0-9_]*`)
     or is in a sentence-adverb blocklist (`i.e`, `e.g`, `etc`, `cf`,
     `vs`, `al`, `viz`, `approx`, `yes`, `no`, `true`, `false`).
     This stops tokens like `i.e.` (which spaCy tags NOUN inside
     parentheticals) and stray `-` (tagged NOUN as an apposition) from
     being promoted to classes and then emitted as malformed
     relationship endpoints.
  2. `candidate.py::_normalise` runs `_sanitise_body`, a defensive
     post-processor that drops any line containing a relationship
     arrow whose source or target identifier is missing or in the
     same blocklist. Acts as a safety net for any future regression.

## Self-author attribution

The author of this benchmark, Vasiliy Seibert, first wrote this
spaCy-based heuristic in 2024 as part of the
`ai4se_benchmarkPaper` companion repository
(`benchmark/candidates/rule_based/utils.py`). It is re-used here with
the same algorithm but with cleaner module packaging and explicit
attribution to Abdelnabi et al. (2020).

## Dependencies (pinned)

| Dependency | Version | License | Purpose |
|---|---|---|---|
| `spacy` | 3.8.x (locally 3.8.14) | MIT | NLP pipeline |
| `en_core_web_sm` | 3.8.0 | MIT | English language model (OntoNotes 5 + ClearNLP + WordNet 3.0) |

### spaCy citation

```bibtex
@software{spacy3,
  author  = {Honnibal, Matthew and Montani, Ines and
             Van Landeghem, Sofie and Boyd, Adriane and {Explosion AI}},
  title   = {spaCy: Industrial-Strength Natural Language Processing in Python},
  year    = {2020},
  version = {3.8},
  doi     = {10.5281/zenodo.1212303},
  url     = {https://spacy.io/}
}
```

To install:

```bash
pip install 'spacy>=3.7,<4.0'
python -m spacy download en_core_web_sm==3.8.0
```

## Files

| File           | Purpose                                              |
|----------------|------------------------------------------------------|
| `candidate.py` | Thin wrapper exposing module-level `candidate`; conforms to the `Candidate` Protocol. |
| `run.py`       | Per-candidate driver; chains `generate.py` → `score.py` → `visualise.py`. |
| `metric.json`  | `{"default_metric": "metrik-1"}` — read by `run.py`. |
| `heuristic.py` | Self-contained spaCy pipeline (parse + 5 extractors). |
| `config.json`  | Legacy discovery metadata from the deleted registry. Not currently read. |
| `README.md`    | This file. |

## No skip folders

The rule-based candidate has no LLM call and no few-shot examples, so
nothing in the evaluation set is excluded.

## Prerequisites

The candidate uses spaCy. Install once before first use:

```bash
pip install 'spacy>=3.7,<4.0'
python -m spacy download en_core_web_sm==3.8.0
```

If spaCy is not installed, every record is recorded as `failed=True`
in the generated JSON and surfaces in `_errors.csv`; the pipeline does
not crash.

## How to run

End-to-end through the per-candidate driver:

```bash
PYTHONPATH=. python Candidates/rule_based/run.py \
    --dataset kaiser_clean
```

Useful flags:

```bash
# First 3 records only
PYTHONPATH=. python Candidates/rule_based/run.py \
    --dataset reference_clean --limit 3

# Override the default metric (rule_based/metric.json ships metrik-1)
PYTHONPATH=. python Candidates/rule_based/run.py \
    --dataset kaiser_clean --metric metrik-4

# Re-run only the visualiser (skip generate + score)
PYTHONPATH=. python Candidates/rule_based/run.py \
    --dataset kaiser_clean --skip-generate --skip-score
```

Under the hood the driver invokes the three workflow steps:

```bash
PYTHONPATH=. python Workflow/Benchmark-Workflow/generate.py  --candidate Candidates/rule_based/candidate.py --dataset ... --out ...
PYTHONPATH=. python Workflow/Benchmark-Workflow/score.py     --in ...
PYTHONPATH=. python Workflow/Benchmark-Workflow/visualise.py --in ..._scored.json --out-dir ... --metric ...
```

Outputs land in `Workflow/Results/rule_based/` by default:
`<dataset>.json`, `<dataset>_scored.json`, `_summary.csv`,
`_summary.json`, `_bucket_<dataset>_<element>_<metric>.csv`,
`_errors.csv`, and `heatmap_<dataset>_<element>_<metric>.png`.

See `Candidates/adjustments.md` for the migration history.