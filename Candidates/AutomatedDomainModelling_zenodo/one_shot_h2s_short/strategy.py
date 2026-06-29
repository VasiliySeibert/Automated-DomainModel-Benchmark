"""AutomatedDomainModelling_zenodo / one_shot_h2s_short — chat-form
one-shot with H2S-Short as the example.

Faithful re-implementation of `generate_prompts_chatgpt` with
`shots=["H2S-Short"]` from `AutomatedDomainModelling_zenodo (the reconstruction in the local sibling repo) — see Candidates/AutomatedDomainModelling_zenodo/README.md` §3b.

The H2S-Short row in upstream `models.csv` is the *short* description
("H2S collects second hand articles ..." without the CoT annotations).
In our dataset the corresponding folder is `HelpingHands`.

Upstream defaults: `temperature=0.7`, `num_predict=1024`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ._ollama import call as call_llm
from Candidates.AutomatedDomainModelling_zenodo._messages import flatten
from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
    text_to_plantuml,
)

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
    """Mimic `generate_prompts_chatgpt` with shots=["H2S-Short"] (zenodo §3b)."""
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
            "error": "zenodo_one_shot_h2s_short_no_plantuml",
            "raw_excerpt": raw[:2000],
        }
    except Exception as exc:
        return {
            "generated_model": "", "failed": True,
            "error": f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt": "",
        }


__all__ = ["run"]