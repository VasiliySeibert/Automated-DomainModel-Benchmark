"""AutomatedDomainModelling-zenodo / cot — one-shot COT with H2S annotated
example (zenodo §5).

The LLM is given a single user message containing the annotated H2S
description (sentence-by-sentence `->` arrows showing which classes /
relationships are derived from each sentence) followed by the target
spec. The model is expected to produce its own reasoning chain.

This reuses the zenodo `generate_prompts_chatgpt_COT` pattern: the
annotated example has NO assistant turn (the model is supposed to
produce the rationale itself), and the prompt contains:
    Description: <annotated H2S>

    Description: {nlt}

The strategy then post-processes the response with `text_to_plantuml()`.
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
_ANNOTATED = _THIS_DIR / "annotated_example.txt"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _build_user_prompt(nlt: str) -> str:
    """Mimic zenodo §5 chat COT format."""
    system = _PROMPT_SYSTEM.read_text(encoding="utf-8")
    annotated = _ANNOTATED.read_text(encoding="utf-8")
    return (
        f"{system}\n\n"
        f"Description:\n{annotated}\n\n"
        f"Description: {nlt}"
    )


def run(spec: CandidateSpec, nlt: str) -> dict:
    user = _build_user_prompt(nlt)
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
            "error": "zenodo_cot_no_plantuml",
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
    strategy="cot",
    uses_llm=True,
    skip_folders=("H2S", "H2S-Short", "HelpingHands"),
    timeout=600,
    description="One-shot COT with H2S annotated example (sentence-by-sentence -> arrows).",
)


register(SPEC)
__all__ = ["SPEC", "run"]