"""AutomatedDomainModelling-zenodo / one_shot_h2s_short — single-call,
H2S-Short example.

Reuses zenodo §3 prompt format. Skips `H2S` (the variant was "H2S-Short"
in the original paper but the dataset folder is `HelpingHands`).
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
    """Mimic zenodo §3 one-shot H2S-Short format."""
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
            "error": "zenodo_one_shot_h2s_short_no_plantuml",
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
    strategy="one_shot_h2s_short",
    uses_llm=True,
    skip_folders=("H2S-Short", "HelpingHands"),
    timeout=600,
    description="Single-call one-shot with H2S-Short example.",
)


register(SPEC)
__all__ = ["SPEC", "run"]