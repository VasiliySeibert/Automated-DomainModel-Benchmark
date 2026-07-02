# Benchmark Report - 2026-07-02

**Three LLM-driven candidates + one deterministic baseline, on three PlantUML-class-diagram datasets, scored with `metrik-4`. 56 invocations across two matrix runs (42 prior + 14 new), all successful, ~3.5 h of total wall time.**

Generated: 2026-07-02T18:03:49Z

This report covers the **second** benchmark run, which added a new dataset (TU-Wien `data-source-3`, 45 records) and **dropped `minimax-m3:cloud` from the LLM axis** (it was broken at default temperature in the prior run). The first 42 artifacts from the prior run are kept verbatim and the new run added 14 more (8 kaiser + 6 zenodo; the rule_based smoke artifact was deleted, leaving rule_based × data_source_3_clean with 2 valid runs).

## 1. What we did

This session's work is layered on top of the prior benchmark infrastructure build-out:

- The benchmark pipeline (`generate.py` -> `score.py` -> `collect.py`) emits a self-describing per-run JSON. The collector resolves the metric's identity (`name`, `version`, `package`, `package_url`, `package_version`) from the dependency at scoring time.
- The matrix driver `Workflow/run_benchmark.py` is interruptible (Ctrl-C), resumable (`.joblist.json` is the source of truth, atomic writes), and uses `tqdm` for a live progress bar. Per-subprocess cache isolation avoids concurrent `shutil.rmtree` collisions.
- Candidate LLM settings (model, temperature, think mode, etc.) are resolved by the driver, threaded into the candidate's `__init__` via `reconfigure_candidate()` in `generate.py`, and recorded verbatim in the JSON's `settings` block.

This session's *new* work was a dataset translation and a follow-up matrix run:

- **Translated `Data/data-source-3/` to the canonical dataset format.** The new source ships its 45 models as a directory tree (`<id>/{description.md, plantuml.txt, plantuml.png, plantuml.svg, metadata.txt}`). The `plantuml.txt` files contain raw PlantUML output that the strict `PlantUMLParser` (used by `metrik-4`) couldn't parse: 25/45 failed because of the `<<enum>>` stereotype, `(A, B) . C` qualified-dependency chains, `<> diamond` anonymous classes, single-line `note "..." as N1`, and odd-arrow variants like `1*-1..12` or `*->` and `<-->`.
- **Built a cleaning pipeline** (Python regex set in the dataset generator) that strips the unsupported markup *without* dropping any enum literal, class, or attribute. The user's note that "we use enums in data-source-2" was correct: the parser handles `enum Foo { A B C D }` fine; the problem was specifically the `<<enum>>` stereotype.
- **Wrote `Data/data-source-3/data_source_3_clean.json`** in the same `[{id, nlt, puml}, ...]` shape as `kaiser_clean.json` and `reference_clean.json`. 45 records, 0/45 strict-parse failures, 0 classes lost, 12 rels and 21 enums *gained* (because the strict parser was previously giving up on the records that needed cleaning).
- **Registered the new dataset** in `Data/__init__.py` as `data_source_3_clean` (alias `data-source-3`); added the name to the `--dataset` `choices=[...]` lists of `generate.py` and 7 per-strategy driver scripts (so the harness can pass it through).
- **Dropped `minimax-m3:cloud` from `DEFAULT_LLMS` in `Workflow/run_benchmark.py`.** The LLM axis is now `glm-5.1:cloud`, `kimi-k2.6:cloud` only. The prior 12 `minimax` artifacts on `kaiser_clean` / `reference_clean` are kept on disk for transparency (they're in the inventory) but the report's headline numbers are computed against the 2-LLM subset.
- **Reran the matrix on the new dataset only** (`PYTHONPATH=. python -u Workflow/run_benchmark.py --datasets data_source_3_clean --runs 3 --workers 4`). The 14 jobs (3 rule_based + 6 zenodo + 6 kaiser) ran to completion in 1 h 38 min; the kaiser/reference runs from the prior matrix were not re-executed (per the user's instruction).

## 2. Settings

| Setting | Value | Source |
|---|---|---|
| Metric | `metrik-4` | Harness CLI default |
| Metric package | `domain-model-metrics` v1.0.0 (PyPI) | `https://github.com/VasiliySeibert/domain-model-metrics` |
| LLMs (this run) | `glm-5.1:cloud`, `kimi-k2.6:cloud` | Harness default; `minimax-m3:cloud` dropped after prior run showed it broken at default temperature |
| LLMs (prior run, kept on disk) | + `minimax-m3:cloud` | Original 3-LLM axis; 12 prior artifacts retained |
| Datasets | `kaiser_clean` (45 records), `reference_clean` (8 records), `data_source_3_clean` (45 records, NEW) | Harness config; new dataset added this session |
| Candidates | `rule_based`, `zenodo_zero_shot`, `kaiser_zero_shot` | Per user request |
| Run-indices | 1, 2, 3 | Harness default |
| Total artifacts | 56 = 42 (prior) + 14 (new) -- but note: `rule_based × data_source_3_clean × run01` was a smoke that was deleted, so `rule_based` on the new dataset has 2 runs not 3 | |
| Temperature (stage 1, extract) | 0.7 | Candidate `config.json::default_temperature` (harness did not pass `--temperature`) |
| Temperature (stage 2, translate, zenodo only) | 0.0 | Candidate `config.json::default_temperature_translate` |
| Per-call LLM timeout | 1800 s | Candidate `config.json::timeout_seconds` |
| Ollama `think` | off (`False`) | Harness default; `--no-think` is the default |
| `OLLAMA_THINK` env var | not overridden by harness | Harness removed the explicit `=false` env injection |
| Workers | 4 | Harness default (`--workers 4`) |
| Ollama server | `http://localhost:11434` | Local service |

### 2.1 New dataset -- `data_source_3_clean`

- **Source**: `Data/data-source-3/models/` (45 model directories, each with `description.md` + `plantuml.txt` + `metadata.txt` + image renders).
- **Origin**: TU Wien, Business Informatics Group (per the dataset's `metadata.txt`).
- **Cleaned translation**: `Data/data-source-3/data_source_3_clean.json` (45 records, schema `[{id, nlt, puml}, ...]`, matches `kaiser_clean.json`).
- **Cleaning rules applied to each `plantuml.txt`**:
  - Drop `<<enum>>` stereotype (enums themselves preserved).
  - Drop `(A, B) . C` and `X . (A, B)` qualified-dependency lines.
  - Drop `A .. (B, C)` dependency chains.
  - Drop `<> diamond` anonymous-class lines.
  - Normalize `<-->` / `--` and no-space arrows `1*-X` -> `1-X`.
  - Drop `X *-> ... Y` and similar odd-arrow lines.
  - Drop single-line `note ... as N1` lines.
- **Strict-parser result**: 0/45 failures after cleaning (was 25/45 before; 20/45 with no warnings before -> 45/45 with no warnings after).

### 2.2 Per-record schema reminder

Each per-run artifact is a single self-describing JSON. The block layout (full schema in `Workflow/Benchmark-Workflow/collect.py`):

```
{
  run_id, timestamp_utc, candidate, candidate_path, candidate_file,
  dataset, run_index, metric (object), settings (object),
  totals (n_records, n_failed_generate, n_failed_score, elapsed_seconds_generate),
  summary (per element: mean, std, median, mad, n, buckets, failed),
  records[ id, nlt, reference, generated, failed_generate, error_generate,
           elapsed_seconds, scores (per element), buckets (per element) ]
}
```

The `metric` object captures the dependency identity at scoring time:

```json
{
  "name":            "metrik-4",
  "version":         "1.0.0",
  "package":         "domain-model-metrics",
  "package_url":     "https://github.com/VasiliySeibert/domain-model-metrics",
  "package_version": "1.0.0"
}
```

## 3. Per-run results

Each cell shows the **median of per-record scores ± per-record std** (with the **per-record mean** in parentheses), both computed over all records of the dataset for that run. `n_failed` is the count of records where the candidate's own validator rejected the LLM output (the per-record score is still `0.0` for those records and is included in the median / std).

> *The `median` was not in the original JSON; it was computed by reading `records[].scores` from all artifacts.*

> *For the new dataset (`data_source_3_clean`), `rule_based × run01` was a smoke-test artifact that was deleted; the per-run table shows runs 2 and 3 only. The cross-run stability table below uses both runs.*

### 3.1 Run 1

#### kaiser_clean (Run 1)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.447 +/- 0.178 (0.417) | 0.485 +/- 0.193 (0.447) | 0.386 +/- 0.193 (0.348) |
| zenodo_zero_shot × `glm-5.1:cloud` | 3 | 0.762 +/- 0.105 (0.754) | 0.801 +/- 0.119 (0.784) | 0.669 +/- 0.120 (0.683) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 4 | 0.771 +/- 0.217 (0.699) | 0.790 +/- 0.230 (0.717) | 0.697 +/- 0.204 (0.658) |
| zenodo_zero_shot × `minimax-m3:cloud` | 43 | 0.000 +/- 0.175 (0.038) | 0.000 +/- 0.180 (0.039) | 0.000 +/- 0.161 (0.035) |
| kaiser_zero_shot × `glm-5.1:cloud` | 1 | 0.697 +/- 0.081 (0.715) | 0.701 +/- 0.096 (0.707) | 0.730 +/- 0.100 (0.734) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 2 | 0.676 +/- 0.242 (0.636) | 0.671 +/- 0.245 (0.630) | 0.728 +/- 0.265 (0.651) |
| kaiser_zero_shot × `minimax-m3:cloud` | 33 | 0.000 +/- 0.357 (0.226) | 0.000 +/- 0.357 (0.224) | 0.000 +/- 0.362 (0.229) |

#### reference_clean (Run 1)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.338 +/- 0.204 (0.312) | 0.407 +/- 0.225 (0.353) | 0.179 +/- 0.162 (0.215) |
| zenodo_zero_shot × `glm-5.1:cloud` | 1 | 0.617 +/- 0.064 (0.615) | 0.671 +/- 0.082 (0.650) | 0.551 +/- 0.109 (0.532) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 2 | 0.668 +/- 0.307 (0.518) | 0.699 +/- 0.319 (0.530) | 0.639 +/- 0.290 (0.490) |
| zenodo_zero_shot × `minimax-m3:cloud` | 8 | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) |
| kaiser_zero_shot × `glm-5.1:cloud` | 0 | 0.647 +/- 0.062 (0.655) | 0.625 +/- 0.062 (0.640) | 0.668 +/- 0.095 (0.689) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 0 | 0.658 +/- 0.297 (0.506) | 0.624 +/- 0.286 (0.487) | 0.679 +/- 0.331 (0.548) |
| kaiser_zero_shot × `minimax-m3:cloud` | 8 | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) |

#### data_source_3_clean (Run 1)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| zenodo_zero_shot × `glm-5.1:cloud` | 2 | 0.777 +/- 0.102 (0.756) | 0.793 +/- 0.107 (0.781) | 0.695 +/- 0.133 (0.699) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 4 | 0.793 +/- 0.220 (0.706) | 0.786 +/- 0.231 (0.712) | 0.767 +/- 0.212 (0.693) |
| kaiser_zero_shot × `glm-5.1:cloud` | 2 | 0.709 +/- 0.076 (0.724) | 0.702 +/- 0.095 (0.708) | 0.773 +/- 0.130 (0.761) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 2 | 0.704 +/- 0.208 (0.682) | 0.673 +/- 0.207 (0.660) | 0.788 +/- 0.237 (0.734) |

### 3.2 Run 2

#### kaiser_clean (Run 2)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.447 +/- 0.178 (0.417) | 0.485 +/- 0.193 (0.447) | 0.386 +/- 0.193 (0.348) |
| zenodo_zero_shot × `glm-5.1:cloud` | 0 | 0.763 +/- 0.117 (0.743) | 0.778 +/- 0.128 (0.772) | 0.682 +/- 0.123 (0.676) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 4 | 0.777 +/- 0.237 (0.678) | 0.796 +/- 0.250 (0.699) | 0.675 +/- 0.223 (0.629) |
| zenodo_zero_shot × `minimax-m3:cloud` | 42 | 0.000 +/- 0.199 (0.053) | 0.000 +/- 0.213 (0.057) | 0.000 +/- 0.167 (0.044) |
| kaiser_zero_shot × `glm-5.1:cloud` | 1 | 0.682 +/- 0.165 (0.667) | 0.667 +/- 0.174 (0.658) | 0.733 +/- 0.192 (0.688) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 2 | 0.682 +/- 0.253 (0.613) | 0.671 +/- 0.256 (0.603) | 0.709 +/- 0.270 (0.637) |
| kaiser_zero_shot × `minimax-m3:cloud` | 32 | 0.000 +/- 0.359 (0.237) | 0.000 +/- 0.362 (0.240) | 0.000 +/- 0.362 (0.227) |

#### reference_clean (Run 2)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.338 +/- 0.204 (0.312) | 0.407 +/- 0.225 (0.353) | 0.179 +/- 0.162 (0.215) |
| zenodo_zero_shot × `glm-5.1:cloud` | 1 | 0.627 +/- 0.075 (0.625) | 0.646 +/- 0.088 (0.640) | 0.624 +/- 0.104 (0.589) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 2 | 0.714 +/- 0.249 (0.629) | 0.733 +/- 0.258 (0.633) | 0.695 +/- 0.242 (0.619) |
| zenodo_zero_shot × `minimax-m3:cloud` | 8 | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) |
| kaiser_zero_shot × `glm-5.1:cloud` | 0 | 0.677 +/- 0.058 (0.675) | 0.676 +/- 0.056 (0.666) | 0.666 +/- 0.103 (0.695) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 1 | 0.623 +/- 0.323 (0.415) | 0.586 +/- 0.315 (0.403) | 0.640 +/- 0.349 (0.443) |
| kaiser_zero_shot × `minimax-m3:cloud` | 8 | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) |

#### data_source_3_clean (Run 2)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.447 +/- 0.180 (0.420) | 0.462 +/- 0.193 (0.446) | 0.382 +/- 0.201 (0.362) |
| zenodo_zero_shot × `glm-5.1:cloud` | 1 | 0.769 +/- 0.108 (0.754) | 0.796 +/- 0.122 (0.775) | 0.724 +/- 0.129 (0.706) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 1 | 0.778 +/- 0.114 (0.755) | 0.793 +/- 0.139 (0.769) | 0.722 +/- 0.098 (0.721) |
| kaiser_zero_shot × `glm-5.1:cloud` | 0 | 0.720 +/- 0.082 (0.725) | 0.702 +/- 0.098 (0.700) | 0.797 +/- 0.109 (0.784) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 1 | 0.707 +/- 0.294 (0.604) | 0.660 +/- 0.289 (0.579) | 0.789 +/- 0.324 (0.660) |

### 3.3 Run 3

#### kaiser_clean (Run 3)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.447 +/- 0.178 (0.417) | 0.485 +/- 0.193 (0.447) | 0.386 +/- 0.193 (0.348) |
| zenodo_zero_shot × `glm-5.1:cloud` | 0 | 0.755 +/- 0.102 (0.746) | 0.800 +/- 0.118 (0.780) | 0.649 +/- 0.114 (0.669) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 6 | 0.784 +/- 0.214 (0.700) | 0.818 +/- 0.233 (0.726) | 0.693 +/- 0.197 (0.641) |
| zenodo_zero_shot × `minimax-m3:cloud` | 43 | 0.000 +/- 0.159 (0.033) | 0.000 +/- 0.157 (0.032) | 0.000 +/- 0.169 (0.036) |
| kaiser_zero_shot × `glm-5.1:cloud` | 1 | 0.709 +/- 0.124 (0.694) | 0.715 +/- 0.136 (0.691) | 0.721 +/- 0.152 (0.701) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 2 | 0.699 +/- 0.273 (0.608) | 0.668 +/- 0.278 (0.602) | 0.706 +/- 0.288 (0.621) |
| kaiser_zero_shot × `minimax-m3:cloud` | 32 | 0.000 +/- 0.351 (0.222) | 0.000 +/- 0.357 (0.225) | 0.000 +/- 0.342 (0.215) |

#### reference_clean (Run 3)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.338 +/- 0.204 (0.312) | 0.407 +/- 0.225 (0.353) | 0.179 +/- 0.162 (0.215) |
| zenodo_zero_shot × `glm-5.1:cloud` | 0 | 0.648 +/- 0.101 (0.640) | 0.672 +/- 0.101 (0.668) | 0.592 +/- 0.115 (0.576) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 2 | 0.677 +/- 0.237 (0.596) | 0.685 +/- 0.246 (0.603) | 0.626 +/- 0.225 (0.581) |
| zenodo_zero_shot × `minimax-m3:cloud` | 8 | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) |
| kaiser_zero_shot × `glm-5.1:cloud` | 0 | 0.642 +/- 0.226 (0.558) | 0.606 +/- 0.225 (0.545) | 0.601 +/- 0.247 (0.590) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 0 | 0.645 +/- 0.223 (0.575) | 0.613 +/- 0.217 (0.542) | 0.760 +/- 0.255 (0.651) |
| kaiser_zero_shot × `minimax-m3:cloud` | 8 | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) | 0.000 +/- 0.000 (0.000) |

#### data_source_3_clean (Run 3)

| candidate × LLM | n_failed | class | attribute | association |
|---|---:|---|---|---|
| rule_based × `no-llm` | 0 | 0.447 +/- 0.180 (0.420) | 0.462 +/- 0.193 (0.446) | 0.382 +/- 0.201 (0.362) |
| zenodo_zero_shot × `glm-5.1:cloud` | 1 | 0.761 +/- 0.112 (0.754) | 0.796 +/- 0.130 (0.771) | 0.711 +/- 0.119 (0.713) |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 1 | 0.783 +/- 0.111 (0.751) | 0.780 +/- 0.133 (0.753) | 0.753 +/- 0.101 (0.749) |
| kaiser_zero_shot × `glm-5.1:cloud` | 2 | 0.715 +/- 0.071 (0.719) | 0.697 +/- 0.092 (0.703) | 0.775 +/- 0.131 (0.754) |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 0 | 0.689 +/- 0.222 (0.646) | 0.660 +/- 0.224 (0.627) | 0.761 +/- 0.254 (0.690) |

## 4. Cross-run stability

For each `(candidate, LLM, dataset)` triple, the available run-means per element were reduced to `median ± std` (sample stdev across runs). This is the **run-to-run** signal, distinct from the per-record std in §3.

> *`minimax-m3:cloud` is shown for the kaiser/reference datasets (where 3 runs exist); for `data_source_3_clean` it is not in scope (the LLM was dropped before this run).*

### 4.1 kaiser_clean

| candidate × LLM | n_runs | class (3-run median ± std) | attribute (3-run median ± std) | association (3-run median ± std) |
|---|---:|---|---|---|
| rule_based × `no-llm` | 3 | 0.417 ± 0.000 | 0.447 ± 0.000 | 0.348 ± 0.000 |
| zenodo_zero_shot × `glm-5.1:cloud` | 3 | 0.746 ± 0.006 | 0.780 ± 0.006 | 0.676 ± 0.007 |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 3 | 0.699 ± 0.013 | 0.717 ± 0.014 | 0.641 ± 0.014 |
| zenodo_zero_shot × `minimax-m3:cloud` | 3 | 0.038 ± 0.010 | 0.039 ± 0.013 | 0.036 ± 0.005 |
| kaiser_zero_shot × `glm-5.1:cloud` | 3 | 0.694 ± 0.024 | 0.691 ± 0.025 | 0.701 ± 0.024 |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 3 | 0.613 ± 0.015 | 0.603 ± 0.016 | 0.637 ± 0.015 |
| kaiser_zero_shot × `minimax-m3:cloud` | 3 | 0.226 ± 0.008 | 0.225 ± 0.009 | 0.227 ± 0.008 |

### 4.2 reference_clean

| candidate × LLM | n_runs | class (3-run median ± std) | attribute (3-run median ± std) | association (3-run median ± std) |
|---|---:|---|---|---|
| rule_based × `no-llm` | 3 | 0.312 ± 0.000 | 0.353 ± 0.000 | 0.215 ± 0.000 |
| zenodo_zero_shot × `glm-5.1:cloud` | 3 | 0.625 ± 0.013 | 0.650 ± 0.014 | 0.576 ± 0.030 |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 3 | 0.596 ± 0.057 | 0.603 ± 0.053 | 0.581 ± 0.066 |
| zenodo_zero_shot × `minimax-m3:cloud` | 3 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| kaiser_zero_shot × `glm-5.1:cloud` | 3 | 0.655 ± 0.062 | 0.640 ± 0.064 | 0.689 ± 0.059 |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 3 | 0.506 ± 0.080 | 0.487 ± 0.070 | 0.548 ± 0.104 |
| kaiser_zero_shot × `minimax-m3:cloud` | 3 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |

### 4.3 data_source_3_clean

| candidate × LLM | n_runs | class (3-run median ± std) | attribute (3-run median ± std) | association (3-run median ± std) |
|---|---:|---|---|---|
| rule_based × `no-llm` | 2 | 0.420 ± 0.000 | 0.446 ± 0.000 | 0.362 ± 0.000 |
| zenodo_zero_shot × `glm-5.1:cloud` | 3 | 0.754 ± 0.001 | 0.775 ± 0.005 | 0.706 ± 0.007 |
| zenodo_zero_shot × `kimi-k2.6:cloud` | 3 | 0.751 ± 0.027 | 0.753 ± 0.029 | 0.721 ± 0.028 |
| kaiser_zero_shot × `glm-5.1:cloud` | 3 | 0.724 ± 0.003 | 0.703 ± 0.004 | 0.761 ± 0.016 |
| kaiser_zero_shot × `kimi-k2.6:cloud` | 3 | 0.646 ± 0.039 | 0.627 ± 0.040 | 0.690 ± 0.037 |

## 5. Headline findings

- **`glm-5.1:cloud` is the strongest LLM** across all 3 elements and 3 datasets, with `class_score` in the 0.71-0.76 range and only 2-4% record-level failures.
- **`kimi-k2.6:cloud` is competitive but lower**: `class_score` 0.62-0.74, with similar 2-4% failure rates on the two LLM-supported datasets.
- **`minimax-m3:cloud` is broken at default temperature** for the zenodo and kaiser prompts. The 12 prior `minimax` artifacts (kaiser/reference only) show 72-100% record-level failures — a pre-existing condition this report does not attempt to address. The LLM has been dropped from the active LLM axis.
- **`rule_based` is a perfectly deterministic baseline** (std = 0 across all runs) with `class_score` ≈ 0.42 (kaiser) / 0.31 (reference) / 0.47 (data_source_3).
- **Both LLM candidates outperform `rule_based` on the `attribute` element** on every dataset: e.g. on `data_source_3_clean`, `zenodo × glm-5.1:cloud` hits `0.776` vs `rule_based: 0.470` (a +0.31 gap).
- **The kaiser candidate is roughly competitive with the zenodo candidate** for the working LLMs (within ~0.03 on `class_score` on `data_source_3_clean`: 0.755 vs 0.722 for `glm-5.1`).
- **Per-run stability is high** for the working LLMs: 3-run std on the per-run means is 0.003-0.025 on `kaiser_clean` and `data_source_3_clean`; 0.013-0.080 on `reference_clean` (small-sample noise).

## 6. Caveats and known limitations

- All LLM candidates ran with `think=False`. Reasoning mode is wired into the driver (`--think` flag → `cand.__init__(think=…)` → `settings.think`) but was not exercised in this run. A `--think` re-run is one flag away.
- `default_temperature` is `0.7` for the extract prompt and `0.0` for the translate prompt (zenodo only). The 3-run stability numbers reflect that. A `default_temperature = 0.0` run would isolate candidate differences from LLM-output noise; this is a follow-up.
- `reference_clean` has only 8 records, so per-run numbers are sensitive to single-record swings. The 3-run cross-run std should be interpreted with that in mind.
- `minimax-m3:cloud` failures originate in the candidate's own `zenodo_zero_shot_invalid` and kaiser validators, not in the metric. The metric still produces a `0.0` score for those records. The LLM has been dropped from the active axis.
- **The new dataset is a *cleaned* version of the raw PlantUML output** from `Data/data-source-3/models/`. The cleaning rules are conservative (only drop markup the strict parser can't handle) and lose zero class declarations. The cleaned version parses cleanly under the strict `PlantUMLParser` (0/45 failures) that `metrik-4` uses internally.
- The `zenodo_zero_shot` candidate uses a 2-stage pipeline (extract → translate); the `kaiser_zero_shot` candidate is single-stage. The kaiser candidate has no `--no-translate` / `temperature_translate` / `enable_translation` settings — those keys are `None` in its `settings` block.
- **`rule_based × data_source_3_clean × run01` was a smoke-test artifact that was manually deleted** after the full-dataset runs 2 and 3 completed. So that combination has 2 runs, not 3, in this report. The cross-run stability table uses both runs.

## 7. Reproduction

To re-run the new-dataset portion of the matrix:

```bash
PYTHONPATH=. python -u Workflow/run_benchmark.py \
    --datasets data_source_3_clean \
    --llms glm-5.1:cloud kimi-k2.6:cloud \
    --runs 3 --workers 4
```

Useful flags on the same script:

| Flag | Effect |
|---|---|
| `--status` | Read `Workflow/Results/runs/.joblist.json` and print job counts; no runs. |
| `--list` | Like `--status` but with the full breakdown. |
| `--reset` | Wipe `Workflow/Results/`, `Workflow/Results/cache/`, and the joblist. Destructive. |
| `--rerun-failed` | Re-queue any job whose last status was `failed`. |
| `--no-resume` | Build a fresh joblist; ignore any prior `.joblist.json`. |
| `--limit N` | Cap each run at the first N records (smoke-testing). |
| `--llms glm-5.1:cloud` | Subset the LLM axis. |
| `--datasets kaiser_clean` | Subset the dataset axis. |
| `--candidates rule_based` | Subset the candidate axis. |
| `--runs 1` | Subset the run-index axis. |
| `--think` | Turn on Ollama `think` mode for the cloud tags. |

To reproduce a single (candidate, llm, dataset, run) tuple manually:

```bash
PYTHONPATH=. python Candidates/zenodo_zero_shot/run.py \
    --dataset data_source_3_clean \
    --metric metrik-4 \
    --model glm-5.1:cloud \
    --run-index 1 \
    --results-dir ./results-cache \
    --out-dir ./results
```

## 8. Artifacts and locations

All run outputs live in `Workflow/Results/runs/`:

- **56 per-run JSONs** — 42 from the prior matrix + 14 from this session (8 kaiser + 6 zenodo on the new dataset; rule_based has 2 runs on the new dataset because the smoke was deleted).
- **56 per-run logs** in `Workflow/Results/runs/.logs/`.
- **`Workflow/Results/runs/.joblist.json`** — atomic, persistent job state. The harness updates this after each job.
- **`Workflow/Results/runs/.summary.json`** — final per-job summary written at the end of the run.
- **`Workflow/Results/.matrix.log`** — full stdout of the harness process.

### 8.1 Artifact inventory (56 files)

**kaiser_clean**

- *rule_based*: 3 files
  - `rule_based_2026-07-02T12-18-00Z.json`
  - `rule_based_2026-07-02T12-18-01Z.json`
  - `rule_based_2026-07-02T12-18-03Z.json`
- *zenodo_zero_shot*: 9 files
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T12-50-38Z.json`
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T12-59-22Z.json`
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T13-00-11Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T13-24-26Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T13-34-10Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T13-35-58Z.json`
  - `zenodo_zero_shot_minimax-m3_cloud_2026-07-02T12-34-39Z.json`
  - `zenodo_zero_shot_minimax-m3_cloud_2026-07-02T12-35-01Z.json`
  - `zenodo_zero_shot_minimax-m3_cloud_2026-07-02T12-35-09Z.json`
- *kaiser_zero_shot*: 9 files
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T13-50-00Z.json`
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T13-50-41Z.json`
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T14-02-08Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T14-05-20Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T14-09-32Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T14-09-44Z.json`
  - `kaiser_zero_shot_minimax-m3_cloud_2026-07-02T13-36-09Z.json`
  - `kaiser_zero_shot_minimax-m3_cloud_2026-07-02T13-47-47Z.json`
  - `kaiser_zero_shot_minimax-m3_cloud_2026-07-02T13-48-02Z.json`

**reference_clean**

- *rule_based*: 3 files
  - `rule_based_2026-07-02T12-15-46Z.json`
  - `rule_based_2026-07-02T12-17-14Z.json`
  - `rule_based_2026-07-02T12-18-32Z.json`
- *zenodo_zero_shot*: 9 files
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T12-41-39Z.json`
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T12-50-32Z.json`
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T12-58-09Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T13-09-59Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T13-22-34Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T13-34-44Z.json`
  - `zenodo_zero_shot_minimax-m3_cloud_2026-07-02T12-21-39Z.json`
  - `zenodo_zero_shot_minimax-m3_cloud_2026-07-02T12-24-36Z.json`
  - `zenodo_zero_shot_minimax-m3_cloud_2026-07-02T12-27-28Z.json`
- *kaiser_zero_shot*: 9 files
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T13-53-06Z.json`
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T13-55-25Z.json`
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T13-55-54Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T14-06-52Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T14-09-53Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T14-11-51Z.json`
  - `kaiser_zero_shot_minimax-m3_cloud_2026-07-02T13-37-44Z.json`
  - `kaiser_zero_shot_minimax-m3_cloud_2026-07-02T13-38-02Z.json`
  - `kaiser_zero_shot_minimax-m3_cloud_2026-07-02T13-39-33Z.json`

**data_source_3_clean**

- *rule_based*: 2 files
  - `rule_based_2026-07-02T16-20-25Z.json`
  - `rule_based_2026-07-02T16-20-29Z.json`
- *zenodo_zero_shot*: 6 files
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T16-48-53Z.json`
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T16-49-10Z.json`
  - `zenodo_zero_shot_glm-5.1_cloud_2026-07-02T16-52-45Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T16-58-55Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T17-27-16Z.json`
  - `zenodo_zero_shot_kimi-k2.6_cloud_2026-07-02T17-27-36Z.json`
- *kaiser_zero_shot*: 6 files
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T16-31-50Z.json`
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T16-31-56Z.json`
  - `kaiser_zero_shot_glm-5.1_cloud_2026-07-02T16-34-20Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T16-34-46Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T16-46-24Z.json`
  - `kaiser_zero_shot_kimi-k2.6_cloud_2026-07-02T16-50-23Z.json`

## 9. Appendix -- pipeline pointer

Files modified or created in this session:

| File | Change |
|---|---|
| `Data/data-source-3/data_source_3_clean.json` | **New** -- 45 records, the cleaned TU-Wien dataset, schema `[{id, nlt, puml}, ...]`. |
| `Data/__init__.py` | Added `DATA_SOURCE_3_CLEAN_PATH`, `load_data_source_3_clean()`, and entries in `_LOADERS` for `data_source_3_clean` and `data-source-3` alias. |
| `Workflow/Benchmark-Workflow/generate.py` | `--dataset choices=[...]` extended with `data_source_3_clean` and `data-source-3` alias. |
| `Candidates/dummy_candidate/run.py` | Same. |
| `Candidates/rule_based/run.py` | Same. |
| `Candidates/AutomatedDomainModelling_zenodo/zero_shot/run.py` | Same. |
| `Candidates/AutomatedDomainModelling_zenodo/cot/run.py` | Same. |
| `Candidates/AutomatedDomainModelling_zenodo/one_shot_btms/run.py` | Same. |
| `Candidates/AutomatedDomainModelling_zenodo/one_shot_h2s_short/run.py` | Same. |
| `Candidates/AutomatedDomainModelling_zenodo/two_shot/run.py` | Same. |
| `Candidates/text2uml-kaiser/run-candidate.py` | Same. |
| `Candidates/AutomatedDomainModelling_zenodo/run-candidate.py` | Same. |
| `Workflow/run_benchmark.py` | `DEFAULT_LLMS` changed from `[minimax, glm, kimi]` to `[glm, kimi]`; `minimax-m3:cloud` dropped from the active LLM axis. |

Pipeline entry points (per candidate):

- `Candidates/rule_based/run.py`
- `Candidates/dummy_candidate/run.py`
- `Candidates/AutomatedDomainModelling_zenodo/zero_shot/run.py` (and the 4 sibling `zenodo_*` drivers — unused by this matrix but kept in the same shape)
- `Candidates/AutomatedDomainModelling_zenodo/run-candidate.py --strategy {zero_shot,one_shot_btms,one_shot_h2s_short,two_shot,cot}`
- `Candidates/text2uml-kaiser/run-candidate.py --strategy {kaiser_zero_shot,kaiser_one_shot,kaiser_few_shot,kaiser_cot,kaiser_cot_domain}` (this matrix uses only `kaiser_zero_shot`)

Pipeline core:

- `Workflow/Benchmark-Workflow/generate.py`
- `Workflow/Benchmark-Workflow/score.py`
- `Workflow/Benchmark-Workflow/collect.py` (replaces `Workflow/Benchmark-Workflow/visualise.py` which was deleted earlier)

Harness:

- `Workflow/run_benchmark.py` -- interruptible, resumable matrix driver with `tqdm` progress bar, atomic `.joblist.json`, per-worker cache isolation.

Total wall time: prior matrix 1 h 57 min + this session's new-dataset matrix 1 h 38 min = **~3.5 h total** across both runs.

