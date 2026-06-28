"""text2uml-kaiser / one_shot — single-call, with AlphaInsurance example.

Reuses the kaiser shot-base header (from `prompt.txt`) plus the
AlphaInsurance example (from `examples.json`). Skips `AlphaInsurance`
from the evaluation set because the model appears verbatim in the
prompt.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ._ollama import call as call_llm
from Candidates.registry import CandidateSpec, register

_THIS_DIR = Path(__file__).resolve().parent
_PROMPT_PATH = _THIS_DIR / "prompt.txt"
_EXAMPLES_PATH = _THIS_DIR / "examples.json"
_MODEL_TAG = "{nlt}"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _safe_substitute(template: str, nlt: str) -> str:
    return template.replace(_MODEL_TAG, nlt)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def _build_user_prompt(examples: list[dict], nlt: str) -> str:
    """Mimic kaiser's `_PROMPT_ONE_SHOT` template — base + 1 example + new spec."""
    blocks = []
    for ex in examples:
        blocks.append(
            "##############\n\n"
            "Here is an example of how should be done.\n\n"
            "The specificartion example text is:\n\n"
            f"{ex['nlt']}\n\n"
            "The corresponding uml is:\n\n"
            f"{ex['model']}\n"
        )
    blocks.append(
        "##############\n\n"
        "The specification text is:\n\n"
        f"{nlt}\n\n"
        "##############\n\n"
        "Based on the example, the uml output is:\n"
    )
    return "\n".join(blocks)


def run(spec: CandidateSpec, nlt: str) -> dict:
    system = _PROMPT_PATH.read_text(encoding="utf-8")
    examples = json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))["examples"]
    user = _build_user_prompt(examples, nlt)
    try:
        raw = call_llm(
            model=spec.model, system=system, prompt=user, timeout=spec.timeout,
        )
        puml = _extract_plantuml(raw) or ""
        if not puml:
            return {
                "generated_model": "",
                "failed": True,
                "error": "no_plantuml_block_in_output",
                "raw_excerpt": raw[:2000],
            }
        return {
            "generated_model": puml,
            "failed": False,
            "error": None,
            "raw_excerpt": raw[:2000],
        }
    except Exception as exc:
        return {
            "generated_model": "",
            "failed": True,
            "error": f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt": "",
        }


SPEC = CandidateSpec(
    source="text2uml-kaiser",
    strategy="one_shot",
    uses_llm=True,
    skip_folders=("AlphaInsurance",),
    timeout=600,
    description="Single-call one-shot with AlphaInsurance example.",
)


register(SPEC)
__all__ = ["SPEC", "run"]