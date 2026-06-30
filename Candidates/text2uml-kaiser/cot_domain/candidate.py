"""text2uml-kaiser / cot_domain — domain-aware 5-step CoT.

Like ``cot``, but with an explicit noun-extraction step before class
selection:

    NLT
      │
      ▼
    [STEP 1 LLM]   prompt_step1_noun.txt           → nouns
      │
      ▼
    [STEP 2 LLM]   prompt_step2_class.txt         → [A, B, C] (refined)
      │
      ▼
    [STEP 3 LLM]   prompt_step3_assoc.txt         → ASSOCIATIONS: ... INHERITANCE: ...
      │
      ▼
    [STEP 2b LLM]  prompt_step2b_attr.txt        → {A: attrs, B: attrs, ...}
      │
      ▼
    [STEP 5 LLM]   system=prompt_step5_plantuml_system.txt
                   user=prompt_step5_plantuml_user.txt
                                                    → @startuml...@enduml
      │
      ▼
    [VALIDATOR]    plantuml_validator.validate
      │            (auto-repair where mechanical, fail otherwise)
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
_PROMPTS = {
    "step1":       _THIS_DIR / "prompt_step1_noun.txt",
    "step2":       _THIS_DIR / "prompt_step2_class.txt",
    "step3":       _THIS_DIR / "prompt_step3_assoc.txt",
    "step2b":      _THIS_DIR / "prompt_step2b_attr.txt",
    "step5system": _THIS_DIR / "prompt_step5_plantuml_system.txt",
    "step5user":   _THIS_DIR / "prompt_step5_plantuml_user.txt",
}

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


def _split_assoc_inh(text: str) -> tuple[str, str]:
    if not text:
        return "", "[]"
    assoc, inh = "", "[]"
    if "ASSOCIATIONS:" in text:
        tail = text.split("ASSOCIATIONS:", 1)[1]
        if "INHERITANCE:" in tail:
            assoc, rest = tail.split("INHERITANCE:", 1)
            inh = rest.strip() or "[]"
        else:
            assoc = tail
    elif "INHERITANCE:" in text:
        inh = text.split("INHERITANCE:", 1)[1].strip() or "[]"
    else:
        assoc = text
    return assoc.strip(), inh.strip() or "[]"


class KaiserCotDomainCandidate:
    """Domain-aware 5-step CoT, with line-by-line validator on the final PUML."""

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
        self._prompts = {k: p.read_text(encoding="utf-8") for k, p in _PROMPTS.items()}

    def __call__(self, nlt: str) -> CandidateOutput:
        try:
            # Step 1: nouns
            step1_user = self._prompts["step1"].replace("{nlt}", nlt)
            step1 = self._call_llm("", step1_user)
            nouns = step1.strip()

            # Step 2: refine nouns → class list
            step2_user = self._prompts["step2"].replace("{noun}", nouns).replace("{nlt}", nlt)
            step2 = self._call_llm("", step2_user)
            classes = step2.strip()
            if not classes:
                return CandidateOutput(
                    generated_model="", failed=True,
                    error="cot_domain_step2_no_classes",
                    raw_excerpt=step2[:2000],
                )

            # Step 3: associations + inheritance
            step3_user = self._prompts["step3"].replace("{classes}", classes).replace("{nlt}", nlt)
            step3 = self._call_llm("", step3_user)
            assoc, inheritance = _split_assoc_inh(step3)

            # Step 2b: attributes
            step2b_user = self._prompts["step2b"].replace("{classes}", classes).replace("{nlt}", nlt)
            step2b = self._call_llm("", step2b_user)
            attributes = step2b.strip() or "{}"

            # Step 5: assemble PlantUML
            step5_user = (self._prompts["step5user"]
                           .replace("{classes}", classes)
                           .replace("{association}", assoc)
                           .replace("{attributes}", attributes)
                           .replace("{inheritance}", inheritance))
            step5_system = self._prompts["step5system"]
            step5 = self._call_llm(step5_system, step5_user)
            puml = _extract_plantuml(step5)
            if not puml:
                return CandidateOutput(
                    generated_model="", failed=True,
                    error="cot_domain_step5_no_plantuml",
                    raw_excerpt=step5[:2000],
                )

            return self._finalise(puml, step5)
        except Exception as exc:
            return CandidateOutput(
                generated_model="", failed=True,
                error=f"exception: {type(exc).__name__}: {exc}",
                raw_excerpt="",
            )

    def _call_llm(self, system: str, user: str) -> str:
        return call_llm(
            model=self.model, system=system, prompt=user,
            timeout=self.timeout,
            temperature=self.temperature,
            num_predict=self.num_predict,
            seed=self.seed, top_p=self.top_p, top_k=self.top_k,
            repeat_penalty=self.repeat_penalty, think=self.think,
        )

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


def _build_default_candidate() -> KaiserCotDomainCandidate:
    cfg = _load_config()
    import os
    model = os.environ.get("OLLAMA_MODEL") or cfg.get("default_model") or "qwen2.5-coder:7b"
    return KaiserCotDomainCandidate(
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


__all__ = ["candidate", "KaiserCotDomainCandidate"]
