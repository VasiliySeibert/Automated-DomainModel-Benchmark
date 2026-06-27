"""text2uml-kaiser / cot — 5-step Chain-of-Thought.

Reuses the kaiser CoT prompts verbatim from src/run.py:
  Step 1: extract class list
  Step 2: extract associations + inheritance
  Step 2b: extract attributes
  Step 3: assign cardinalities
  Step 5: assemble PlantUML

Each step is its own LLM call. The output of each step feeds into the
next step's prompt. If any step fails, the strategy short-circuits with
`failed=True` and the orchestrator records the failure.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from Candidates.ollama.harness import call as call_llm
from Candidates.registry import CandidateSpec, register

_THIS_DIR = Path(__file__).resolve().parent
_PROMPTS = {
    "step1":       _THIS_DIR / "prompt_step1_class.txt",
    "step2":       _THIS_DIR / "prompt_step2_assoc.txt",
    "step2b":      _THIS_DIR / "prompt_step2b_attr.txt",
    "step3":       _THIS_DIR / "prompt_step3_card.txt",
    "step5system": _THIS_DIR / "prompt_step5_plantuml_system.txt",
    "step5user":   _THIS_DIR / "prompt_step5_plantuml_user.txt",
}

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)
_LIST_RE = re.compile(r"\[([^\]]+)\]")


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _extract_class_list(text: str) -> str:
    """Pull [A, B, C] out of the LLM's step-1 output. Fallback: raw text."""
    if not text:
        return ""
    m = _LIST_RE.search(text)
    return ("[" + m.group(1).strip() + "]") if m else text.strip()


def _split_assoc_inh(text: str) -> tuple[str, str]:
    """Split step-2 output into (associations_text, inheritance_text)."""
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
    """Execute the 5-step CoT chain. Any single failure short-circuits."""
    try:
        # Step 1: class list
        step1_user = _PROMPTS["step1"].read_text(encoding="utf-8").replace("{nlt}", nlt)
        step1 = call_llm(model=spec.model, system="", prompt=step1_user, timeout=spec.timeout)
        classes = _extract_class_list(step1)
        if not classes:
            return {
                "generated_model": "", "failed": True,
                "error": "cot_step1_no_classes",
                "raw_excerpt": step1[:2000],
            }

        # Step 2: associations + inheritance
        step2_user = _PROMPTS["step2"].read_text(encoding="utf-8").replace(
            "{classes}", classes
        ).replace("{nlt}", nlt)
        step2 = call_llm(model=spec.model, system="", prompt=step2_user, timeout=spec.timeout)
        assoc, inheritance = _split_assoc_inh(step2)

        # Step 2b: attributes
        step2b_user = _PROMPTS["step2b"].read_text(encoding="utf-8").replace(
            "{classes}", classes
        ).replace("{nlt}", nlt)
        step2b = call_llm(model=spec.model, system="", prompt=step2b_user, timeout=spec.timeout)
        attributes = step2b.strip() or "{}"

        # Step 3: cardinalities
        step3_user = _PROMPTS["step3"].read_text(encoding="utf-8").replace(
            "{association}", assoc
        ).replace("{nlt}", nlt)
        step3 = call_llm(model=spec.model, system="", prompt=step3_user, timeout=spec.timeout)
        card = step3.strip()

        # Step 5: assemble PlantUML
        step5_user = _PROMPTS["step5user"].read_text(encoding="utf-8").replace(
            "{classes}", classes
        ).replace("{card}", card).replace(
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
                "error": "cot_step5_no_plantuml",
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


SPEC = CandidateSpec(
    source="text2uml-kaiser",
    strategy="cot",
    uses_llm=True,
    skip_folders=(),
    timeout=600,
    description="5-step Chain-of-Thought: class list → associations+inheritance → attributes → cardinalities → PlantUML.",
)


register(SPEC)
__all__ = ["SPEC", "run"]