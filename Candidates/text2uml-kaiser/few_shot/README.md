# text2uml-kaiser / few_shot

Single-call few-shot prompt with **two** worked examples:
1. **AlphaInsurance** (NL spec + reference UML).
2. **GasStation** (NL spec + reference UML).

**Skip folders:** `AlphaInsurance`, `GasStation_KUL`, `GasStation_TUW`.

## Files

| File           | Purpose                                                       |
|----------------|---------------------------------------------------------------|
| `prompt.txt`   | Verbatim copy of `_SHOT_BASE` from upstream.                  |
| `examples.json`| Both worked examples.                                          |
| `strategy.py`  | Self-contained strategy.                                      |
| `config.json`  | Discovery metadata.                                           |