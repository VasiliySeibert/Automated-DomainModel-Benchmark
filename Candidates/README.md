# Candidates/

This directory contains every workflow candidate plus the shared
`Candidate` interface.

```
Candidates/
├── candidate_interface.py           # Candidate Protocol + loader (shared)
├── dummy-candidate/                # canonical, deterministic implementation
│   ├── README.md
│   └── candidate.py                # exposes `candidate` callable
│
├── text2uml-kaiser/                # legacy: 5 strategies (not yet wired to Candidate)
├── AutomatedDomainModelling_zenodo/# legacy: 5 strategies (not yet wired)
├── ai4se_benchmarkPaper/           # legacy: 1 strategy (not yet wired)
└── zenodo_text_format.py, _messages.py   # source-group helpers (legacy)
```

## The `Candidate` interface

Defined in
[`Candidates/candidate_interface.py`](candidate_interface.py). Every
candidate is a Python module that exposes a module-level `candidate`
callable conforming to the `Candidate` Protocol:

```python
def candidate(nlt: str) -> CandidateOutput: ...
```

`CandidateOutput` carries `{generated_model, failed, error, raw_excerpt}`.
The workflow calls the candidate once per record, persists the raw
output, scores it in a separate step, and visualises the results. No
candidate-specific knowledge lives in the workflow.

`load_candidate(path)` resolves both `.../candidate.py` and
`.../some-folder/` (looking up `candidate.py` inside).

## The dummy candidate — a worked example

[`dummy-candidate/`](dummy-candidate/) is the canonical implementation:
a deterministic constant-output candidate that ignores the input NLT
and always returns the same hard-coded PlantUML block. Use it to
smoke-test the
[`Workflow`](../Workflow/) pipeline without LLM latency.

```bash
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/dummy_candidate/candidate.py \
    --dataset kaiser_clean
```

## Migrating your own strategy

To wire your own candidate:

```python
# Candidates/my_candidate/candidate.py
from Candidates.candidate_interface import CandidateOutput


class MyCandidate:
    def __call__(self, nlt: str) -> CandidateOutput:
        # ... build a PlantUML string from nlt ...
        return CandidateOutput(
            generated_model=puml,
            failed=False,
            error=None,
            raw_excerpt=puml[:2000],
        )


candidate = MyCandidate()
```

```bash
PYTHONPATH=. python Workflow/run_all.py \
    --candidate Candidates/my_candidate/candidate.py \
    --dataset kaiser
```

The workflow takes care of dataset iteration, scoring, aggregation,
and visualisation.

## Legacy strategies

The 11 pre-existing strategies under `text2uml-kaiser/`,
`AutomatedDomainModelling_zenodo/`, and
`ai4se_benchmarkPaper/rule_based/` were written for the previous
registry-based workflow. They still ship their verbatim prompts and
inlined `_ollama.py` HTTP wrappers, but their `SPEC` / `register()`
calls have been removed and they are not yet wired to the new
`Candidate` interface. Migrating each one is a follow-up — wrap its
`run()` in a class with `__call__(self, nlt)` and expose a module-level
`candidate` instance.