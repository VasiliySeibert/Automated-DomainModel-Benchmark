"""AutomatedDomainModelling_zenodo / cot — chat-form Chain-of-Thought
with H2S annotated example.

Faithful re-implementation of `generate_prompts_chatgpt_COT` from
`AutomatedDomainModelling_zenodo (the reconstruction in the local sibling repo) — see Candidates/AutomatedDomainModelling_zenodo/README.md` §5. The example provides
only the H2S **description** annotated with `->` arrows (sentence by
sentence, showing which classes / relationships are derived from each
sentence) — but **no assistant answer**. The model is expected to
produce the reasoning chain itself.

    [
        {"role": "system", "content": "Generate the lists of model classes
                                     and associations from a given description."},
        {"role": "user",   "content": "Description: <H2S annotated description>"},
        {"role": "user",   "content": <new description>},
    ]

The annotated H2S row lives in `models_cot.csv` (verbatim `Description`
field; `Classes` and `Associations` are empty). In our dataset the
folders are `H2S`, `H2S-Short`, `HelpingHands`.

Upstream defaults: `temperature=0.7`, `num_predict=1024`.
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
_ANNOTATED = _THIS_DIR / "annotated_example.txt"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _build_messages(annotated: str, nlt: str) -> list[dict]:
    """Mimic `generate_prompts_chatgpt_COT` (zenodo §5) — no assistant turn."""
    return [
        {"role": "system", "content": _PROMPT_SYSTEM.read_text(encoding="utf-8")},
        {"role": "user",   "content": f"Description:\n{annotated}\n"},
        {"role": "user",   "content": nlt},
    ]


def run(spec: CandidateSpec, nlt: str) -> dict:
    annotated = _ANNOTATED.read_text(encoding="utf-8")
    system, user = flatten(_build_messages(annotated, nlt))
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
            "error": "zenodo_cot_no_plantuml",
            "raw_excerpt": raw[:2000],
        }
    except Exception as exc:
        return {
            "generated_model": "", "failed": True,
            "error": f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt": "",
        }


__all__ = ["run"]