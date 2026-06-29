"""AutomatedDomainModelling_zenodo / zero_shot — chat-form zero-shot.

Faithful re-implementation of `generate_prompts_chatgpt` with `shots=[]`
from `AutomatedDomainModelling_zenodo (the reconstruction in the local sibling repo) — see Candidates/AutomatedDomainModelling_zenodo/README.md` §1b:

    [
        {"role": "system", "content": "Generate the lists of model classes
                                     and associations from a given description."},
        {"role": "user",   "content": <TASK_DESCRIPTION>},
        {"role": "user",   "content": <description>},
    ]

The inlined `_ollama.py` HTTP wrapper exposes only one `system` slot
plus one `user` slot, so the upstream 3-turn chat list is flattened
via the group-shared
`Candidates.AutomatedDomainModelling_zenodo._messages.flatten` helper:
the system message becomes the harness `system=` argument; the two user
turns are concatenated with a `USER:` label between them.

If the LLM emits a PlantUML block directly (some instruction-tuned models
do), we use it as-is. Otherwise we parse the zenodo text format and
synthesise a PlantUML block via `zenodo_text_format.text_to_plantuml`.

Uses upstream defaults: `temperature=0.7`, `num_predict=1024`
(see `AutomatedDomainModelling_zenodo (the reconstruction in the local sibling repo) — see Candidates/AutomatedDomainModelling_zenodo/README.md` config.yaml).
"""
from __future__ import annotations

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
_PROMPT_TASK = _THIS_DIR / "prompt_task.txt"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _build_messages(nlt: str) -> list[dict]:
    """Mimic `generate_prompts_chatgpt` with shots=[] (zenodo §1b)."""
    return [
        {"role": "system", "content": _PROMPT_SYSTEM.read_text(encoding="utf-8")},
        {"role": "user",   "content": _PROMPT_TASK.read_text(encoding="utf-8")},
        {"role": "user",   "content": nlt},
    ]


def run(spec: CandidateSpec, nlt: str) -> dict:
    system, user = flatten(_build_messages(nlt))
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
            "error": "zenodo_zero_shot_no_plantuml_no_text_format",
            "raw_excerpt": raw[:2000],
        }
    except Exception as exc:
        return {
            "generated_model": "", "failed": True,
            "error": f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt": "",
        }


__all__ = ["run"]