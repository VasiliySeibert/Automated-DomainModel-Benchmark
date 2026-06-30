"""AutomatedDomainModelling_zenodo / zero_shot — two-stage LLM candidate.

Architecture (migrated to the new ``Candidate`` interface — see
``Candidates/adjustments.md``):

    NLT
      │
      ▼
    [STAGE 1 LLM]  system=prompt_system.txt, task=prompt_task.txt, user=NLT
      │            (the verbatim zenodo §1b zero-shot prompt)
      ▼
    DSL response (Enumeration:/Class:/Relationships: text)
      │
      ▼
    [DSL → PUML]  zenodo_text_format.text_to_plantuml
      ▼
    Intermediate PUML (may be malformed — that's fine, stage 2 will fix it)
      │
      ▼
    [STAGE 2 LLM]  system=prompt_translate.txt, user=intermediate PUML
      │            (translation prompt that encodes the metrik-4 grammar)
      ▼
    Final PUML response
      │
      ▼
    [VALIDATOR]    plantuml_validator.validate
      │            (line-by-line, auto-repair where mechanical, fail otherwise)
      ▼
    CandidateOutput(generated_model, failed, error, raw_excerpt)

If ``enable_translation`` is False (set via ``--no-translate`` on
``run.py``), the candidate skips stage 2 and validates the
intermediate PUML directly. This is the A/B fallback.

The module-level ``candidate`` singleton is populated from
``config.json`` and the ``OLLAMA_MODEL`` env var. ``run.py`` can
re-instantiate it in place via ``candidate.__init__(...)``.

Conforms to the ``Candidate`` Protocol from
``Candidates/candidate_interface.py`` by exposing a module-level
``candidate`` callable.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from _ollama import call as call_llm
from Candidates.AutomatedDomainModelling_zenodo._messages import flatten
from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format import (
    text_to_plantuml,
)
from Candidates.AutomatedDomainModelling_zenodo.plantuml_validator import (
    validate as validate_puml,
    ValidateResult,
)
from Candidates.candidate_interface import CandidateOutput

log = logging.getLogger(__name__)

_THIS_DIR = Path(__file__).resolve().parent
_CFG_PATH = _THIS_DIR / "config.json"
_PROMPT_SYSTEM = _THIS_DIR / "prompt_system.txt"
_PROMPT_TASK = _THIS_DIR / "prompt_task.txt"
_PROMPT_TRANSLATE = _THIS_DIR / "prompt_translate.txt"

_PLANTUML_BLOCK = re.compile(r"@startuml.*?@enduml", re.DOTALL | re.IGNORECASE)


def _load_defaults() -> dict:
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


class TwoStageZeroShotCandidate:
    """Chat-form zero-shot LLM candidate with stage 2 translation + validator.

    Ignores any model parameter — this strategy is LLM-driven, so the
    ``model`` argument is required. The LLM is queried twice per
    record unless ``enable_translation`` is False.
    """

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        temperature_translate: float = 0.0,
        num_predict: int = 1024,
        seed: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        timeout: int = 600,
        enable_translation: bool = True,
        think: bool = False,
    ):
        self.model = model
        self.temperature = temperature
        self.temperature_translate = temperature_translate
        self.num_predict = num_predict
        self.seed = seed
        self.top_p = top_p
        self.top_k = top_k
        self.repeat_penalty = repeat_penalty
        self.timeout = timeout
        self.enable_translation = enable_translation
        self.think = think
        self._prompt_system = _PROMPT_SYSTEM.read_text(encoding="utf-8")
        self._prompt_task = _PROMPT_TASK.read_text(encoding="utf-8")
        self._prompt_translate = _PROMPT_TRANSLATE.read_text(encoding="utf-8")

    def __call__(self, nlt: str) -> CandidateOutput:
        stage1 = self._stage1(nlt)
        if stage1.failed:
            return stage1

        if not self.enable_translation:
            intermediate = _extract_plantuml(stage1.raw_excerpt)
            if not intermediate:
                intermediate = text_to_plantuml(stage1.raw_excerpt)
            if not intermediate:
                return CandidateOutput(
                    generated_model="",
                    failed=True,
                    error="zenodo_zero_shot_stage1_no_puml",
                    raw_excerpt=stage1.raw_excerpt,
                )
            return self._finalise(intermediate, stage1.raw_excerpt,
                                  error_prefix="zenodo_zero_shot_invalid")

        raw_dsl = stage1.raw_excerpt
        stage2 = self._stage2(raw_dsl)
        if stage2.failed:
            return stage2

        final_puml = _extract_plantuml(stage2.raw_excerpt)
        if not final_puml:
            return CandidateOutput(
                generated_model="",
                failed=True,
                error="zenodo_zero_shot_stage2_no_puml",
                raw_excerpt=stage2.raw_excerpt,
            )

        return self._finalise(final_puml, stage2.raw_excerpt,
                              error_prefix="zenodo_zero_shot_invalid")

    def _stage1(self, nlt: str) -> CandidateOutput:
        messages = [
            {"role": "system", "content": self._prompt_system},
            {"role": "user", "content": self._prompt_task},
            {"role": "user", "content": nlt},
        ]
        system, user = flatten(messages)
        try:
            raw = call_llm(
                model=self.model,
                system=system,
                prompt=user,
                timeout=self.timeout,
                temperature=self.temperature,
                num_predict=self.num_predict,
                seed=self.seed,
                top_p=self.top_p,
                top_k=self.top_k,
                repeat_penalty=self.repeat_penalty,
                think=self.think,
            )
            return CandidateOutput(
                generated_model="", failed=False, error=None,
                raw_excerpt=raw[:2000],
            )
        except Exception as exc:
            return CandidateOutput(
                generated_model="", failed=True,
                error=f"exception: {type(exc).__name__}: {exc}",
                raw_excerpt="",
            )

    def _stage2(self, intermediate_puml: str) -> CandidateOutput:
        try:
            raw = call_llm(
                model=self.model,
                system=self._prompt_translate,
                prompt=intermediate_puml,
                timeout=self.timeout,
                temperature=self.temperature_translate,
                num_predict=self.num_predict,
                seed=self.seed,
                top_p=self.top_p,
                top_k=self.top_k,
                repeat_penalty=self.repeat_penalty,
                think=self.think,
            )
            return CandidateOutput(
                generated_model="", failed=False, error=None,
                raw_excerpt=raw[:2000],
            )
        except Exception as exc:
            return CandidateOutput(
                generated_model="", failed=True,
                error=f"exception: {type(exc).__name__}: {exc}",
                raw_excerpt="",
            )

    def _finalise(self, puml: str, raw_excerpt: str, error_prefix: str) -> CandidateOutput:
        result: ValidateResult = validate_puml(puml)
        if result.ok and result.repaired:
            return CandidateOutput(
                generated_model=result.repaired,
                failed=False,
                error=None,
                raw_excerpt=raw_excerpt,
            )
        return CandidateOutput(
            generated_model=result.repaired or "",
            failed=True,
            error=f"{error_prefix}: {' | '.join(result.errors)[:500]}",
            raw_excerpt=raw_excerpt,
        )


def _build_default_candidate() -> TwoStageZeroShotCandidate:
    cfg = _load_defaults()
    model = (
        os.environ.get("OLLAMA_MODEL")
        or cfg.get("default_model")
        or "qwen2.5-coder:7b"
    )
    return TwoStageZeroShotCandidate(
        model=model,
        temperature=cfg.get("default_temperature", 0.7),
        temperature_translate=cfg.get("default_temperature_translate", 0.0),
        num_predict=cfg.get("default_num_predict", 1024),
        seed=cfg.get("default_seed"),
        top_p=cfg.get("default_top_p"),
        top_k=cfg.get("default_top_k"),
        repeat_penalty=cfg.get("default_repeat_penalty"),
        timeout=cfg.get("timeout_seconds", 600),
        enable_translation=cfg.get("enable_translation", True),
    )


candidate = _build_default_candidate()


__all__ = ["candidate", "TwoStageZeroShotCandidate"]
