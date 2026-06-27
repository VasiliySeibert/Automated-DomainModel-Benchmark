# ai4se_benchmarkPaper / rule_based

spaCy SVO + verb-lemma heuristic. Reused verbatim from
`ai4se_benchmarkPaper/benchmark/candidates/rule_based/utils.py`.

**No LLM.** `spec.model` is ignored. `uses_llm=False` in the registry.

## Pre-requisite

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

If these are missing, the strategy returns `failed=True` with a clear
error message — the orchestrator records the failure but does not
abort the batch.