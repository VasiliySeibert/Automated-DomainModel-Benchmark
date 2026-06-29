"""text2uml-kaiser / zero_shot — single-call direct generation.

Reuses the system prompt verbatim from `text2uml-kaiser/src/run.py::
_ZERO_SHOT_SYSTEM` (loaded from `prompt.txt` next to this file) and the
user template `"Transform into plant uml this specification text: {nlt}"`.

Imports the inlined `_ollama.py` HTTP wrapper at the top of the file.

NOTE: This strategy predates the `Candidate` interface in
`Candidates/candidate_interface.py`. It is **not yet wired** to the new
Workflow — the orchestrator currently only knows about the dummy.
Migration is a follow-up.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ._ollama import call as call_llm

_THIS_DIR = Path(__file__).resolve().parent
_PROMPT_PATH = _THIS_DIR / "prompt.txt"
_USER_TEMPLATE = "Transform into plant uml this specification text: {nlt}"
_MODEL_TAG = "{nlt}"

# Where the LLM's response is allowed to embed a PlantUML block.
_PLANTUML_BLOCK = re.compile(
    r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE
)


def _safe_substitute(template: str, nlt: str) -> str:
    """Replace `{nlt}` literally without touching other `{ }` in the template."""
    return template.replace(_MODEL_TAG, nlt)


def _extract_plantuml(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PLANTUML_BLOCK.search(text)
    return m.group(0).strip() if m else None


def run(spec: CandidateSpec, nlt: str) -> dict:
    """Run the zero-shot strategy on the given natural-language spec."""
    system = _PROMPT_PATH.read_text(encoding="utf-8")
    user = _safe_substitute(_USER_TEMPLATE, nlt)
    try:
        raw = call_llm(
            model=spec.model,
            system=system,
            prompt=user,
            timeout=spec.timeout,
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


__all__ = ["run"]