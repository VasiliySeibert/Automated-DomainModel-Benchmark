# Data/NLP-Analysis

NLP analysis of the three domain-model datasets
(`kaiser_clean`, `reference_clean`, `data_source_3_clean`).

The goal is to quantify (a) the shape of each reference PlantUML
diagram, (b) the shape of its natural-language text (NLT), and (c) how
well the diagram elements can be recovered from the NLT by lexical and
dependency-graph matching.

## How to run

```bash
# 1. Install deps
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# 2. Run the full pipeline (analyze → report → summary → examples)
make all
# or step by step:
make analyze
make report
make summary
make examples

# Tests
make test
```

The full run takes ~1 min on a laptop.

## Tests

```bash
PYTHONPATH=. python -m pytest Data/NLP-Analysis/tests/ -q
```

20 tests cover the parser, the four-level lexical matcher, the
dependency-graph binder, the cross-reference diff, and the comparison
summary JSON. One is skipped when only one dataset is loaded.

## Output layout

```
Data/NLP-Analysis/out/
├── summary.json              # SINGLE SOURCE OF TRUTH — every comparison number
├── per_record.csv            # one row per (dataset, id), wide
├── per_record.jsonl          # one JSON object per record: full dep-graph,
│                             # every binding, parser warnings, sentence stats
├── per_element_match.csv     # one row per diagram element with L1..L4
├── cross_dataset.csv         # Jaccard of element sets, kaiser vs data_source_3
├── rel_kind_coverage.csv     # per-(dataset, id, rel_kind) coverage
├── nlt_sentence_stats.csv    # per-sentence class/attr/rel hits
├── nlt_style.csv             # passive, hedge, modal, entity density per record
├── parser_warnings.csv       # every parser warning, with dataset and id
├── summary.md                # auto-generated tables (markdown)
├── charts/                   # 6 PNG charts
│   ├── chart_nlt_vs_classes.png
│   ├── chart_rel_type_distribution.png
│   ├── chart_attr_lexical_coverage.png
│   ├── chart_pct_bound.png
│   ├── chart_correlation_heatmap.png
│   └── chart_cross_dataset_jaccard.png
└── examples/                 # 5 case-study markdown pages
```

## Documents

- [`INSIGHTS.md`](./INSIGHTS.md) — 15 insights with LaTeX tables ready
  to drop into a paper. Each number is a slice of `out/summary.json`.
- [`FINDINGS.md`](./FINDINGS.md) — the methodology: how the parser,
  lexical matcher, dep-graph binder, and cross-reference diff are
  implemented, plus narrative findings.
- `out/summary.md` — auto-generated tables (markdown).
- `out/summary.json` — machine-readable canonical numbers.
- `out/charts/*.png` — the six charts.
- `out/examples/*.md` — the five hand-picked case studies.
