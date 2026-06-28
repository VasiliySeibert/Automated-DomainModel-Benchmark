"""Direct HTTP harness for the Ollama API.

The ollama harness is the **default** for every LLM-driven prompt
strategy. It POSTs to `/api/chat` on a local Ollama server (default
`http://localhost:11434`, override via `$OLLAMA_HOST`).

Why this instead of opencode?
* No shell-out latency — pure HTTP, no subprocess.
* No "system prompt" CLI flag workaround needed.
* Direct control over the message structure.

Public API:
    call(model, system, prompt, *, timeout=600,
         temperature=None, num_predict=None) -> str
        POSTs the prompt to the configured Ollama server and returns
        the assistant message content.
    is_available() -> bool
        Cheap health check — returns True if the configured Ollama
        server is reachable.
"""
from __future__ import annotations

import json
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
) -> str:
    """Call the Ollama chat API and return the assistant message.

    Args:
        model:       the model tag visible to `ollama list`, e.g. `minimax-m3:cloud`.
        system:      the system-prompt string. If empty, no system message is sent.
        prompt:      the user-prompt string.
        timeout:     hard wall-clock timeout in seconds.
        temperature: optional sampling temperature (e.g. 0.0 for deterministic,
                     0.7 for the zenodo upstream default). `None` uses the
                     Ollama server's default for the model.
        num_predict: optional max-output-tokens cap. `None` uses the Ollama
                     server default.

    Returns:
        The assistant message content as a string.

    Raises:
        requests.HTTPError: on non-2xx HTTP responses.
        requests.ConnectionError: if the Ollama server is not reachable.
        KeyError: if the response payload does not contain `message.content`.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    options: dict = {}
    if temperature is not None:
        options["temperature"] = float(temperature)
    if num_predict is not None:
        options["num_predict"] = int(num_predict)
    if options:
        payload["options"] = options

    url = f"{host()}/api/chat"
    log.info("ollama POST %s model=%s prompt=%d chars", url, model, len(prompt))
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    return body["message"]["content"].strip()


def is_available() -> bool:
    """Return True iff the Ollama server responds to `/api/tags`."""
    try:
        r = requests.get(f"{host()}/api/tags", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def list_models() -> list[str]:
    """Return the list of model tags visible to the local Ollama server."""
    r = requests.get(f"{host()}/api/tags", timeout=10)
    r.raise_for_status()
    body = r.json()
    return [m["name"] for m in body.get("models", [])]


__all__ = ["call", "host", "is_available", "list_models", "DEFAULT_TIMEOUT"]