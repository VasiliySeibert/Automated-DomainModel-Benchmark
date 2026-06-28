"""AutomatedDomainModelling_zenodo / one_shot_btms — chat-form one-shot
with BTMS as the example.

Faithful re-implementation of `generate_prompts_chatgpt` with
`shots=["BTMS"]` from `AutomatedDomainModelling-zenodo/prompts.md` §2b:

    [
        {"role": "system",    "content": "Generate the lists of model classes
                                         and associations from a given description."},
        {"role": "user",      "content": "Description: <BTMS description>"},
        {"role": "assistant", "content": "<BTMS classes> \n\n  Relationships:
                                          <BTMS associations>\n\n"},
        {"role": "user",      "content": <new description>},
    ]

The BTMS shot is the row from `models.csv` (verbatim `Description`,
`Classes`, `Associations` columns). Skips `BTMS` from the evaluation
set because the case appears verbatim in the prompt.

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
    """Mimic `generate_prompts_chatgpt` with shots=["BTMS"] (zenodo §2b).

    Note the upstream uses `prompt_generation.py:101`:
        f"{classes_shot} \\n\\n  Relationships:\\n{associations_shot}\\n\\n"
    which produces the `\\n\\n  Relationships:` separator we mirror here.
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
            "error": "zenodo_one_shot_btms_no_plantuml",
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
    strategy="one_shot_btms",
    uses_llm=True,
    skip_folders=("BTMS",),
    timeout=600,
    temperature=0.7,
    num_predict=1024,
    description=(
        "One-shot chat form (zenodo §2b): system + BTMS user/assistant "
        "shot pair + new description. Skips BTMS from the evaluation set."
    ),
)


register(SPEC)
__all__ = ["SPEC", "run"]