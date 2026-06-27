"""AutomatedDomainModelling-zenodo / zero_shot — emits zenodo text format,
then converts it to PlantUML.

Reuses `PROBLEM_STATEMENT` (from `prompt_system.txt`) and
`TASK_DESCRIPTION` (from `prompt_task.txt`) verbatim from
`AutomatedDomainModelling-zenodo/prompts.md` §1.

The LLM is prompted to emit a structured text response of the form:

    Enumeration:
    EnumName(literal1, literal2, ...)

    Class:
    ClassName(type1 attrName1, type2 attrName2)
    abstract ClassName(...)

    Relationships:
    mul1 class1 associate mul2 class2
    mul1 class1 contain mul2 class2
    class1 inherit class2

If the LLM emits a PlantUML block directly (some instruction-tuned
models do), we use it as-is. Otherwise we parse the text format and
synthesise a PlantUML block via the bundled `_text_to_plantuml` helper.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from Candidates.ollama.harness import call as call_llm
from Candidates.registry import CandidateSpec, register

_THIS_DIR = Path(__file__).resolve().parent
_PROMPT_SYSTEM = _THIS_DIR / "prompt_system.txt"
_PROMPT_TASK = _THIS_DIR / "prompt_task.txt"
_USER_TEMPLATE = "{nlt}"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _build_user_prompt(nlt: str) -> str:
    system = _PROMPT_SYSTEM.read_text(encoding="utf-8")
    task = _PROMPT_TASK.read_text(encoding="utf-8")
    return f"{system}\n\n{task}\n\nDescription:\n{nlt}\n\nEnumeration:\nClasses:\n\nRelationships:\n"


def run(spec: CandidateSpec, nlt: str) -> dict:
    user = _build_user_prompt(nlt)
    try:
        raw = call_llm(model=spec.model, system="", prompt=user, timeout=spec.timeout)
        # Try direct PlantUML extraction first.
        puml = _extract_plantuml(raw)
        if puml:
            return {
                "generated_model": puml, "failed": False,
                "error": None, "raw_excerpt": raw[:2000],
            }
        # Otherwise convert the zenodo text format via the group-level helper.
        from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
            text_to_plantuml,
        )
        puml = text_to_plantuml(raw)
        if puml:
            return {
                "generated_model": puml, "failed": False,
                "error": None, "raw_excerpt": raw[:2000],
            }
        return {
            "generated_model": "", "failed": True,
            "error": "zenodo_zero_shot_no_plantuml_no_text_format",
            "raw_excerpt": raw[:2000],
        }
    except Exception as exc:
        return {
            "generated_model": "", "failed": True,
            "error": f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt": "",
        }


SPEC = CandidateSpec(
    source="AutomatedDomainModelling-zenodo",
    strategy="zero_shot",
    uses_llm=True,
    skip_folders=(),
    timeout=600,
    description="Zero-shot with the zenodo text format. Auto-converts to PlantUML.",
)


register(SPEC)
__all__ = ["SPEC", "run"]