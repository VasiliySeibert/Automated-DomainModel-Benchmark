# Candidates/

Eleven self-contained prompt strategies organised in three source
folders. Every strategy is fully self-contained — including its own
copy of the Ollama HTTP wrapper (`_ollama.py`) — so nothing is shared
across strategy folders.

```
Candidates/
├── text2uml-kaiser/                         # 5 strategies (Calamo et al. 2025 + Zenodo 2026)
│   ├── zero_shot/    {strategy.py, _ollama.py, prompt.txt, config.json, README.md}
│   ├── one_shot/     {strategy.py, _ollama.py, prompt.txt, examples.json, config.json, README.md}
│   ├── few_shot/     {strategy.py, _ollama.py, prompt.txt, examples.json, config.json, README.md}
│   ├── cot/          {strategy.py, _ollama.py, prompt_step{1,2,2b,3,5}_*.txt, config.json, README.md}
│   └── cot_domain/   {strategy.py, _ollama.py, prompt_step{1,2,3,2b,5}_*.txt, config.json, README.md}
│
├── AutomatedDomainModelling_zenodo/         # 5 strategies (Chen et al. 2023, MODELS)
│   ├── zero_shot/         {strategy.py, _ollama.py, prompt_{system,task}.txt, config.json, README.md}
│   ├── one_shot_btms/     {strategy.py, _ollama.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── one_shot_h2s_short/{strategy.py, _ollama.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── two_shot/          {strategy.py, _ollama.py, prompt_{system,task}.txt, examples.json, ...}
│   ├── cot/               {strategy.py, _ollama.py, prompt_{system,task}.txt, annotated_example.txt, ...}
│   ├── _messages.py                         # chat-form → (system, user) helper
│   └── zenodo_text_format.py                # text-format → PlantUML converter
│
├── ai4se_benchmarkPaper/                    # 1 strategy (rule-based baseline)
│   └── rule_based/                          # spaCy SVO + verb-lemma heuristic
│                                              # (re-implementation of Abdelnabi 2020)
│
└── registry.py                              # walks the tree, builds spec list
```

## Self-containment rules

1. **Each candidate folder is fully self-contained.** A candidate has
   `strategy.py` + prompt files (`prompt*.txt` / `examples.json` /
   `annotated_example.txt`) + `config.json` + `README.md` + its own
   copy of `_ollama.py` (the LLM HTTP wrapper, byte-identical across
   all 10 LLM-driven strategies — see `tests/test_ollama_inlined.py`).
2. **Each strategy imports its own `_ollama`** with a relative import:
   ```python
   from ._ollama import call as call_llm
   ```
3. **No global shared code.** The only "shared" modules are:
   - `AutomatedDomainModelling_zenodo/zenodo_text_format.py` and
     `AutomatedDomainModelling_zenodo/_messages.py` — shared **within**
     the zenodo source group only.
4. **Registry discovery.** `Candidates/registry.py` walks the tree
   and dynamically imports each `strategy.py`. All source-group folder
   names use underscores so they are normal Python packages.

## Cell matrix

| Source                          | Strategies | × Models | Cells/dataset | × 2 datasets | Records |
|---------------------------------|-----------:|---------:|---------------:|-------------:|--------:|
| `text2uml-kaiser/`              |          5 |        4 |             20 |           40 |      40 |
| `AutomatedDomainModelling_zenodo/` |       5 |        4 |             20 |           40 |      40 |
| `ai4se_benchmarkPaper/rule_based/` |     1 |        1 |              1 |            2 |       2 |
| **TOTAL**                       |     **11** |          |          **41** |       **82** |  **82** |

## Skip rules

Each LLM strategy declares `skip_folders` in its `config.json`. The
orchestrator filters these records before invoking the LLM.

| Strategy                       | Skip folders                              |
|--------------------------------|-------------------------------------------|
| `text2uml-kaiser/zero_shot`    | —                                         |
| `text2uml-kaiser/one_shot`     | `AlphaInsurance`                          |
| `text2uml-kaiser/few_shot`     | `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW` |
| `text2uml-kaiser/cot`          | —                                         |
| `text2uml-kaiser/cot_domain`   | —                                         |
| `AutomatedDomainModelling_zenodo/zero_shot` | —                                |
| `AutomatedDomainModelling_zenodo/one_shot_btms` | `BTMS`                       |
| `AutomatedDomainModelling_zenodo/one_shot_h2s_short` | `H2S-Short`, `HelpingHands` |
| `AutomatedDomainModelling_zenodo/two_shot` | `BTMS`, `H2S-Short`, `HelpingHands` |
| `AutomatedDomainModelling_zenodo/cot` | `H2S`, `H2S-Short`, `HelpingHands` |
| `ai4se_benchmarkPaper/rule_based` | —                                      |

## LLM access (inlined)

Each LLM-driven strategy folder contains its own `_ollama.py` — a
byte-identical copy of the Ollama `/api/chat` HTTP wrapper
(Ollama v0.30.11, MIT). There is no shared harness module: bug fixes
are propagated by copying the updated `_ollama.py` to all 10 strategy
folders (the test `tests/test_ollama_inlined.py::test_all_10_inlined_ollama_copies_are_byte_identical`
enforces this invariant).