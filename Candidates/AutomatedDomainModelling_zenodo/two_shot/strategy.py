"""AutomatedDomainModelling_zenodo / two_shot — chat-form two-shot
with BTMS + H2S-Short as the examples.

Faithful re-implementation of `generate_prompts_chatgpt` with
`shots=["BTMS", "H2S-Short"]` from `AutomatedDomainModelling-zenodo/prompts.md` §4b.

Skips `BTMS`, `H2S-Short`, and `HelpingHands` (the local folder for the
H2S-Short example) from the evaluation set.

Upstream defaults: `temperature=0.7`, `num_predict=1024`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from Candidates.ollama.harness import call as call_llm
from Candidates.AutomatedDomainModelling_zenodo._messages import flatten
from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
    text_to_plantuml,
)
from Candidates.registry import CandidateSpec, register

_THIS_DIR = Path(__file__).resolve().parent
_PROMPT_SYSTEM = _THIS_DIR / "prompt_system.txt"
_EXAMPLES = _THIS_DIR / "examples.json"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _build_messages(examples: list[dict], nlt: str) -> list[dict]:
    """Mimic `generate_prompts_chatgpt` with shots=["BTMS","H2S-Short"] (zenodo §4b).

    The shot order in `examples.json` MUST match the upstream `shots`
    list (BTMS first, H2S-Short second).
    """
    system = _PROMPT_SYSTEM.read_text(encoding="utf-8")
    msgs: list[dict] = [{"role": "system", "content": system}]
    for ex in examples:
        msgs.append({"role": "user",      "content": f"Description: {ex['nlt']}\n"})
        msgs.append({
            "role": "assistant",
            "content": f"{ex['model']} \n\n  Relationships:\n\n",
        })
    msgs.append({"role": "user", "content": nlt})
    return msgs


def run(spec: CandidateSpec, nlt: str) -> dict:
    examples = json.loads(_EXAMPLES.read_text(encoding="utf-8"))["examples"]
    system, user = flatten(_build_messages(examples, nlt))
    try:
        raw = call_llm(
            model=spec.model,
            system=system,
            prompt=user,
            timeout=spec.timeout,
            temperature=spec.temperature,
            num_predict=spec.num_predict,
        )
        puml = _extract_plantuml(raw)
        if puml:
            return {
                "generated_model": puml, "failed": False,
                "error": None, "raw_excerpt": raw[:2000],
            }
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
    source="AutomatedDomainModelling_zenodo",
    strategy="two_shot",
    uses_llm=True,
    skip_folders=("BTMS", "H2S-Short", "HelpingHands"),
    timeout=600,
    temperature=0.7,
    num_predict=1024,
    description=(
        "Two-shot chat form (zenodo §4b): system + BTMS user/assistant "
        "shot pair + H2S-Short user/assistant shot pair + new description."
    ),
)


register(SPEC)
__all__ = ["SPEC", "run"]