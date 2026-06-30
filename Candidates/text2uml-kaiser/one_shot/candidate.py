"""text2uml-kaiser / one_shot — single-call, with AlphaInsurance example.

Architecture (mirrors the kaiser zero_shot pattern):

    NLT
      │
      ▼
    [LLM]   system=prompt.txt
            user=base + 1 example + new spec (############## block format)
      │
      ▼
    Raw PlantUML response
      │
      ▼
    [VALIDATOR]     plantuml_validator.validate
      │             (auto-repair where mechanical, fail otherwise)
      ▼
    Clean PUML  →  CandidateOutput

Conforms to the ``Candidate`` Protocol from
``Candidates/candidate_interface.py`` by exposing a module-level
``candidate`` callable.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from _ollama import call as call_llm
from Candidates.AutomatedDomainModelling_zenodo.plantuml_validator import (
    validate as validate_puml,
    ValidateResult,
)
from Candidates.candidate_interface import CandidateOutput

log = logging.getLogger(__name__)

_CFG_PATH = _THIS_DIR / "config.json"
_PROMPT_PATH = _THIS_DIR / "prompt.txt"
_EXAMPLES_PATH = _THIS_DIR / "examples.json"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _load_config() -> dict:
    try:
        return json.loads(_CFG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("could not read %s: %s", _CFG_PATH, exc)
        return {}


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


class KaiserOneShotCandidate:
    """Single-call one-shot with one example, with line-by-line validator."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        num_predict: int = 1024,
        seed: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        timeout: int = 600,
        think: bool = False,
        **_unused,
    ):
        self.model = model
        self.temperature = temperature
        self.num_predict = num_predict
        self.seed = seed
        self.top_p = top_p
        self.top_k = top_k
        self.repeat_penalty = repeat_penalty
        self.timeout = timeout
        self.think = think
        self._prompt = _PROMPT_PATH.read_text(encoding="utf-8")
        self._examples = json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))["examples"]

    def __call__(self, nlt: str) -> CandidateOutput:
        user = _build_user_prompt(self._examples, nlt)
        try:
            raw = call_llm(
                model=self.model, system=self._prompt, prompt=user,
                timeout=self.timeout,
                temperature=self.temperature,
                num_predict=self.num_predict,
                seed=self.seed, top_p=self.top_p, top_k=self.top_k,
                repeat_penalty=self.repeat_penalty, think=self.think,
            )
        except Exception as exc:
            return CandidateOutput(
                generated_model="", failed=True,
                error=f"exception: {type(exc).__name__}: {exc}",
                raw_excerpt="",
            )

        puml = _extract_plantuml(raw)
        if not puml:
            return CandidateOutput(
                generated_model="", failed=True,
                error="kaiser_one_shot_no_plantuml",
                raw_excerpt=raw[:2000],
            )

        return self._finalise(puml, raw)

    def _finalise(self, puml: str, raw_excerpt: str) -> CandidateOutput:
        result: ValidateResult = validate_puml(puml)
        if result.ok and result.repaired:
            return CandidateOutput(
                generated_model=result.repaired,
                failed=False, error=None,
                raw_excerpt=raw_excerpt,
            )
        return CandidateOutput(
            generated_model=result.repaired or "",
            failed=True,
            error=f"plantuml_validator: {' | '.join(result.errors)[:500]}",
            raw_excerpt=raw_excerpt,
        )


def _build_default_candidate() -> KaiserOneShotCandidate:
    cfg = _load_config()
    import os
    model = os.environ.get("OLLAMA_MODEL") or cfg.get("default_model") or "qwen2.5-coder:7b"
    return KaiserOneShotCandidate(
        model=model,
        temperature=cfg.get("default_temperature", 0.7),
        num_predict=cfg.get("default_num_predict", 1024),
        seed=cfg.get("default_seed"),
        top_p=cfg.get("default_top_p"),
        top_k=cfg.get("default_top_k"),
        repeat_penalty=cfg.get("default_repeat_penalty"),
        timeout=cfg.get("timeout_seconds", 600),
    )


candidate = _build_default_candidate()


__all__ = ["candidate", "KaiserOneShotCandidate"]
