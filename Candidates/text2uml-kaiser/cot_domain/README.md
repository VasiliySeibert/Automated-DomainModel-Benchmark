# text2uml-kaiser / cot_domain

Same shape as `cot`, but with an **explicit noun-extraction step** at
the front of the chain (steps 1 + 2 instead of just step 1). The
kaiser upstream uses different prompt constants (`_DOMAIN_*` vs
`_COT_*`); we replicate the structure here.

```
spec ──► step1 (noun list)
         └► step2 (refined class list)
              └► step3 (associations + inheritance, with multiplicities)
              └► step2b (attributes)
                   └► step5 (PlantUML assembly)
```

## Files

| File                              | Purpose                                          |
|-----------------------------------|--------------------------------------------------|
| `prompt_step1_noun.txt`           | `_DOMAIN_NOUN` verbatim.                          |
| `prompt_step2_class.txt`          | `_DOMAIN_CLASS` verbatim.                         |
| `prompt_step3_assoc.txt`          | `_DOMAIN_ASSOC` verbatim.                         |
| `prompt_step2b_attr.txt`          | `_COT_ATTR` verbatim (reused as `_DOMAIN_ATTR`). |
| `prompt_step5_plantuml_system.txt`| System prompt enforcing parser-compatible syntax.|
| `prompt_step5_plantuml_user.txt`  | `_DOMAIN_PLANT` user template verbatim.           |
| `strategy.py`                     | 5-step chain; imports `Candidates.ollama.harness`. |
| `config.json`                     | Discovery metadata.                              |