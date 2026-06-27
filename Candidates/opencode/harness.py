"""opencode candidate — the opencode-detached LLM harness.

This candidate exposes the `opencode run`-based LLM call as a standalone
strategy. It is **not** used as the default harness by any of the
prompt-strategy candidates (those import `Candidates.ollama.harness`).

Public API:
    call(model_id: str, system: str, prompt: str, *, timeout: int = 600) -> str
        Subprocess call to `opencode run` with the given message.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess

log = logging.getLogger(__name__)


def _opencode_path() -> str:
    """Locate the opencode binary; honours $OPENCODE_BIN override."""
    override = os.environ.get("OPENCODE_BIN")
    if override:
        return override
    found = shutil.which("opencode")
    if found is None:
        raise FileNotFoundError(
            "opencode binary not found on PATH. Install opencode or set "
            "$OPENCODE_BIN."
        )
    return found


def call(
    model_id: str,
    system: str,
    prompt: str,
    *,
    timeout: int = 600,
) -> str:
    """Run `opencode run` with the given message, return its stdout.

    The system instructions are prepended to the user message because
    opencode's CLI does not expose a system-prompt flag.

    Args:
        model_id: the opencode model id, e.g. `ollama/glm-5.1:cloud`.
        system:   optional system instructions.
        prompt:   user message.
        timeout:  hard wall-clock timeout in seconds.

    Returns:
        Decoded stdout (trailing whitespace stripped).

    Raises:
        subprocess.TimeoutExpired: if the run exceeds `timeout`.
        FileNotFoundError: if the opencode binary is not on PATH.
    """
    full_message = f"{system.strip()}\n\n{prompt}" if system else prompt

    cmd = [
        _opencode_path(),
        "run",
        full_message,
        "--model", model_id,
        "--format", "default",
    ]
    log.info(
        "opencode run: model=%s timeout=%ds msg=%d chars",
        model_id, timeout, len(full_message),
    )
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        log.error(
            "opencode exit %d: %s", proc.returncode,
            (proc.stderr or "")[:500],
        )
    return proc.stdout.strip()


__all__ = ["call"]