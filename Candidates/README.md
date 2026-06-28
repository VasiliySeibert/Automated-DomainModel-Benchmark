# Candidates/

Eleven self-contained prompt strategies organised in three source
folders:

```
Candidates/
├── ollama/                                  # default LLM harness
│   ├── harness.py                           # POST /api/chat on $OLLAMA_HOST
│   └── config.json
├── opencode/                                # alternative harness
│   ├── harness.py                           # subprocess to `opencode run`
│   └── config.json
│
├── text2uml-kaiser/                         # 5 strategies (Kaiser 2026)
│   ├── zero_shot/
│   ├── one_shot/                            # skip AlphaInsurance
│   ├── few_shot/                            # skip AlphaInsurance + GasStation
│   ├── cot/                                 # 5-step CoT chain
│   └── cot_domain/                          # 5-step domain CoT chain
│
├── AutomatedDomainModelling_zenodo/         # 5 strategies (Bademoses 2024)
│   ├── zero_shot/
│   ├── one_shot_btms/                       # skip BTMS
│   ├── one_shot_h2s_short/                  # skip H2S-Short + HelpingHands
│   ├── two_shot/                            # skip BTMS + H2S-Short + HelpingHands
│   ├── cot/                                 # skip H2S + H2S-Short + HelpingHands
│   ├── _messages.py                         # chat-form → (system, user) helper
│   └── zenodo_text_format.py                # text-format → PlantUML converter
│
├── ai4se_benchmarkPaper/                    # 1 strategy
│   └── rule_based/                          # spaCy heuristic (no LLM)
│
└── registry.py                              # walks the tree, builds spec list
```

## Self-containment rules

1. **Each candidate folder is fully self-contained.** A candidate has
   `strategy.py` + prompt files (`prompt*.txt` / `examples.json` /
   `annotated_example.txt`) + `config.json` + `README.md`.
2. **Each strategy imports one harness at the top of `strategy.py`**:
   ```python
   from Candidates.ollama.harness import call as call_llm
   ```
   To swap to opencode, change this one line. No other file in the
   candidate needs to change.
3. **No global shared code.** The only "shared" modules are:
   - `ollama/harness.py` and `opencode/harness.py` — the two harnesses
     themselves (each is its own candidate folder).
   - `AutomatedDomainModelling_zenodo/zenodo_text_format.py` — the
     text-to-PlantUML converter shared **within** the zenodo source
     group only (no other group uses it).
   - `AutomatedDomainModelling_zenodo/_messages.py` — chat-form →
     `(system, user)` flattener shared **within** the zenodo source
     group only.
4. **Registry discovery.** `Candidates/registry.py` walks the tree
   and dynamically imports each `strategy.py`. All source-group folders
   use underscores so they are normal Python packages importable via
   dotted notation (e.g. `from Candidates.AutomatedDomainModelling_zenodo
   .zenodo_text_format import text_to_plantuml`).

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

## Harnesses

* **`ollama/`** (default) — direct HTTP POST to the local Ollama
  server. Lower latency than opencode. Read its
  [README](ollama/README.md) for endpoint config.
* **`opencode/`** (alternative) — shells out to `opencode run` in
  detached mode. Slower but available without Ollama being installed.
  Read its [README](opencode/README.md).