"""AutomatedDomainModelling-zenodo / two_shot — single-call with two examples
(BTMS + H2S-Short). Skips BTMS, H2S-Short, HelpingHands.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from Candidates.ollama.harness import call as call_llm
from Candidates.registry import CandidateSpec, register

_THIS_DIR = Path(__file__).resolve().parent
_PROMPT_SYSTEM = _THIS_DIR / "prompt_system.txt"
_PROMPT_TASK = _THIS_DIR / "prompt_task.txt"
_EXAMPLES = _THIS_DIR / "examples.json"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _build_user_prompt(examples: list[dict], nlt: str) -> str:
    """Mimic zenodo §4 two-shot format — task + N examples + new spec."""
    shots: list[str] = []
    for ex in examples:
        shots.append(
            f"Description:\n{ex['nlt']}\n\n{ex['model']}\n\n###\n"
        )
    system = _PROMPT_SYSTEM.read_text(encoding="utf-8")
    task = _PROMPT_TASK.read_text(encoding="utf-8")
    return (
        f"{system}\n\n{task}\n\n"
        + "".join(shots)
        + f"Description:\n{nlt}"
    )


def run(spec: CandidateSpec, nlt: str) -> dict:
    examples = json.loads(_EXAMPLES.read_text(encoding="utf-8"))["examples"]
    user = _build_user_prompt(examples, nlt)
    try:
        raw = call_llm(model=spec.model, system="", prompt=user, timeout=spec.timeout)
        puml = _extract_plantuml(raw)
        if puml:
            return {
                "generated_model": puml, "failed": False,
                "error": None, "raw_excerpt": raw[:2000],
            }
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
            "error": "zenodo_two_shot_no_plantuml",
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
    strategy="two_shot",
    uses_llm=True,
    skip_folders=("BTMS", "H2S-Short", "HelpingHands"),
    timeout=600,
    description="Two-shot with BTMS + H2S-Short examples.",
)


register(SPEC)
__all__ = ["SPEC", "run"]