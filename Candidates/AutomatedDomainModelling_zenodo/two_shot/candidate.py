"""AutomatedDomainModelling_zenodo / two_shot — chat-form two-shot with BTMS + H2S-Short examples.

Architecture (mirrors the zero_shot migration — see
``Candidates/adjustments.md``):

    NLT
      │
      ▼
    [STAGE 1 LLM]   system=prompt_system.txt
                    user=BTMS description, assistant=BTMS model
                    user=H2S-Short description, assistant=H2S-Short model
                    user=target NLT
                    (shot order in examples.json MUST be BTMS, H2S-Short)
      │
      ▼
    Raw DSL / model output
      │
      ▼
    [STAGE 2 LLM]   system=prompt_translate.txt, user=raw stage-1 output
                    temperature 0.0 by default
      │
      ▼
    Final PUML response
      │
      ▼
    [VALIDATOR]     plantuml_validator.validate
      │
      ▼
    CandidateOutput(generated_model, failed, error, raw_excerpt)

If ``--no-translate`` is set on ``run.py``, stage 2 is skipped and the
intermediate output (raw stage-1 response, possibly bridged via
``zenodo_text_format.text_to_plantuml``) is validated directly.

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

_CFG_PATH = _THIS_DIR / "config.json"
_PROMPT_SYSTEM = _THIS_DIR / "prompt_system.txt"
_EXAMPLES = _THIS_DIR / "examples.json"
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


class TwoShotCandidate:
    """Chat-form two-shot LLM candidate with BTMS + H2S-Short examples, stage 2 + validator."""

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
        self._prompt_translate = _PROMPT_TRANSLATE.read_text(encoding="utf-8")
        self._examples = json.loads(_EXAMPLES.read_text(encoding="utf-8"))["examples"]

    def _build_messages(self, nlt: str) -> list[dict]:
        """Mimic `generate_prompts_chatgpt` with shots=["BTMS","H2S-Short"] (zenodo §4b).

        The shot order in ``examples.json`` MUST match the upstream ``shots``
        list (BTMS first, H2S-Short second).
        """
        msgs: list[dict] = [{"role": "system", "content": self._prompt_system}]
        for ex in self._examples:
            msgs.append({"role": "user",      "content": f"Description: {ex['nlt']}\n"})
            msgs.append({
                "role": "assistant",
                "content": f"{ex['model']} \n\n  Relationships:\n\n",
            })
        msgs.append({"role": "user", "content": nlt})
        return msgs

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
                    error="zenodo_two_shot_stage1_no_puml",
                    raw_excerpt=stage1.raw_excerpt,
                )
            return self._finalise(intermediate, stage1.raw_excerpt,
                                  error_prefix="zenodo_zero_shot_invalid")

        stage2 = self._stage2(stage1.raw_excerpt)
        if stage2.failed:
            return stage2

        final_puml = _extract_plantuml(stage2.raw_excerpt)
        if not final_puml:
            return CandidateOutput(
                generated_model="",
                failed=True,
                error="zenodo_two_shot_stage2_no_puml",
                raw_excerpt=stage2.raw_excerpt,
            )

        return self._finalise(final_puml, stage2.raw_excerpt,
                              error_prefix="zenodo_zero_shot_invalid")

    def _stage1(self, nlt: str) -> CandidateOutput:
        system, user = flatten(self._build_messages(nlt))
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

    def _stage2(self, intermediate: str) -> CandidateOutput:
        try:
            raw = call_llm(
                model=self.model,
                system=self._prompt_translate,
                prompt=intermediate,
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


def _build_default_candidate() -> TwoShotCandidate:
    cfg = _load_defaults()
    model = (
        os.environ.get("OLLAMA_MODEL")
        or cfg.get("default_model")
        or "qwen2.5-coder:7b"
    )
    return TwoShotCandidate(
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


__all__ = ["candidate", "TwoShotCandidate"]
