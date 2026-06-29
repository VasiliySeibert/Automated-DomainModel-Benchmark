"""text2uml-kaiser / cot_domain — domain-aware 5-step Chain-of-Thought.

Like `cot`, but with an explicit noun-extraction step before class
selection. The kaiser upstream uses different prompt constants for each
step (`_DOMAIN_*` vs `_COT_*`); we replicate the structure here.

Step 1: extract noun list
Step 2: refine nouns → class list
Step 3: extract associations (with multiplicities) + inheritance
Step 2b: extract attributes (reuses _COT_ATTR)
Step 5: assemble PlantUML
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ._ollama import call as call_llm

_THIS_DIR = Path(__file__).resolve().parent
_PROMPTS = {
    "step1":       _THIS_DIR / "prompt_step1_noun.txt",
    "step2":       _THIS_DIR / "prompt_step2_class.txt",
    "step3":       _THIS_DIR / "prompt_step3_assoc.txt",
    "step2b":      _THIS_DIR / "prompt_step2b_attr.txt",
    "step5system": _THIS_DIR / "prompt_step5_plantuml_system.txt",
    "step5user":   _THIS_DIR / "prompt_step5_plantuml_user.txt",
}

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _split_assoc_inh(text: str) -> tuple[str, str]:
    if not text:
        return "", "[]"
    assoc, inh = "", "[]"
    if "ASSOCIATIONS:" in text:
        tail = text.split("ASSOCIATIONS:", 1)[1]
        if "INHERITANCE:" in tail:
            assoc, rest = tail.split("INHERITANCE:", 1)
            inh = rest.strip() or "[]"
        else:
            assoc = tail
    elif "INHERITANCE:" in text:
        inh = text.split("INHERITANCE:", 1)[1].strip() or "[]"
    else:
        assoc = text
    return assoc.strip(), inh.strip() or "[]"


def run(spec: CandidateSpec, nlt: str) -> dict:
    try:
        # Step 1: extract nouns
        step1_user = _PROMPTS["step1"].read_text(encoding="utf-8").replace("{nlt}", nlt)
        step1 = call_llm(model=spec.model, system="", prompt=step1_user, timeout=spec.timeout)
        nouns = step1.strip()

        # Step 2: refine nouns → class list
        step2_user = _PROMPTS["step2"].read_text(encoding="utf-8").replace(
            "{noun}", nouns
        ).replace("{nlt}", nlt)
        step2 = call_llm(model=spec.model, system="", prompt=step2_user, timeout=spec.timeout)
        classes = step2.strip()
        if not classes:
            return {
                "generated_model": "", "failed": True,
                "error": "cot_domain_step2_no_classes",
                "raw_excerpt": step2[:2000],
            }

        # Step 3: associations + inheritance (with multiplicities embedded)
        step3_user = _PROMPTS["step3"].read_text(encoding="utf-8").replace(
            "{classes}", classes
        ).replace("{nlt}", nlt)
        step3 = call_llm(model=spec.model, system="", prompt=step3_user, timeout=spec.timeout)
        assoc, inheritance = _split_assoc_inh(step3)

        # Step 2b: attributes (reuses kaiser _COT_ATTR)
        step2b_user = _PROMPTS["step2b"].read_text(encoding="utf-8").replace(
            "{classes}", classes
        ).replace("{nlt}", nlt)
        step2b = call_llm(model=spec.model, system="", prompt=step2b_user, timeout=spec.timeout)
        attributes = step2b.strip() or "{}"

        # Step 5: assemble PlantUML
        step5_user = _PROMPTS["step5user"].read_text(encoding="utf-8").replace(
            "{classes}", classes
        ).replace("{association}", assoc).replace(
            "{attributes}", attributes
        ).replace("{inheritance}", inheritance)
        step5_system = _PROMPTS["step5system"].read_text(encoding="utf-8")
        step5 = call_llm(
            model=spec.model, system=step5_system,
            prompt=step5_user, timeout=spec.timeout,
        )
        puml = _extract_plantuml(step5) or ""
        if not puml:
            return {
                "generated_model": "", "failed": True,
                "error": "cot_domain_step5_no_plantuml",
                "raw_excerpt": step5[:2000],
            }
        return {
            "generated_model": puml, "failed": False,
            "error": None, "raw_excerpt": step5[:2000],
        }
    except Exception as exc:
        return {
            "generated_model": "", "failed": True,
            "error": f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt": "",
        }


__all__ = ["run"]