"""Per-strategy Ollama HTTP wrapper.

Self-contained: this file is copied into every LLM-driven strategy
folder so each strategy is fully self-contained (no shared harness
modules). All strategies POST to `${OLLAMA_HOST:-http://localhost:11434}/api/chat`
with the documented Ollama chat API schema.

Upstream: Ollama v0.30.11 — https://github.com/ollama/ollama
(branch `main`, MIT, Copyright (c) Ollama, maintained by Ollama Inc.).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import requests

log = logging.getLogger(__name__)

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT = 600


def host() -> str:
    """Return the configured Ollama host (env override honoured)."""
    return os.environ.get("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")


def call(
    model: str,
    system: str,
    prompt: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    temperature: Optional[float] = None,
    num_predict: Optional[int] = None,
    seed: Optional[int] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    repeat_penalty: Optional[float] = None,
    think: Optional[bool] = None,
) -> str:
    """Call the Ollama chat API and return the assistant message content.

    Args:
        model:          the model tag visible to `ollama list`, e.g. `minimax-m3:cloud`.
        system:         the system-prompt string. If empty, no system message is sent.
        prompt:         the user-prompt string.
        timeout:        hard wall-clock timeout in seconds.
        temperature:    optional sampling temperature (e.g. 0.0 for deterministic,
                        0.7 for the zenodo upstream default). `None` uses the
                        Ollama server's default for the model.
        num_predict:    optional max-output-tokens cap. `None` uses the Ollama
                        server default.
        seed:           optional integer seed for reproducible outputs (Ollama
                        "Reproducible outputs" example). `None` is non-deterministic.
        top_p:          optional nucleus sampling cutoff in (0, 1]. `None` uses
                        the Ollama server default for the model.
        top_k:          optional top-K sampling cutoff (>= 1). `None` uses the
                        Ollama server default for the model.
        repeat_penalty: optional penalty for repeating tokens (>= 0). `None` uses
                        the Ollama server default for the model.

    Returns:
        The assistant message content as a string.

    Raises:
        requests.HTTPError: on non-2xx HTTP responses.
        requests.ConnectionError: if the Ollama server is not reachable.
        KeyError: if the response payload does not contain `message.content`.
    """
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if think is not None:
        payload["think"] = bool(think)
    options: dict = {}
    if temperature is not None:
        options["temperature"] = float(temperature)
    if num_predict is not None:
        options["num_predict"] = int(num_predict)
    if seed is not None:
        options["seed"] = int(seed)
    if top_p is not None:
        options["top_p"] = float(top_p)
    if top_k is not None:
        options["top_k"] = int(top_k)
    if repeat_penalty is not None:
        options["repeat_penalty"] = float(repeat_penalty)
    if options:
        payload["options"] = options

    url = f"{host()}/api/chat"
    log.info("ollama POST %s model=%s prompt=%d chars", url, model, len(prompt))
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    message = body.get("message", {})
    content = message.get("content", "").strip()
    if not content:
        content = message.get("thinking", "").strip()
    return content


__all__ = ["call", "host", "DEFAULT_HOST", "DEFAULT_TIMEOUT"]