"""Build chat-style message lists for the zenodo prompt strategies.

The upstream `AutomatedDomainModelling_zenodo` repo (`prompt_generation.py`)
constructs prompts as a list of `{"role", "content"}` message dicts, exactly
as they would be passed to the OpenAI Chat API. Three patterns are used:

  * `generate_prompts_chatgpt` (zero-shot, one-shot, two-shot):
        system + (optional user/assistant shot pairs) + final user task.
  * `generate_prompts_chatgpt_COT` (chain-of-thought):
        system + one user message with the annotated example + final user task
        with the target description. **No assistant turn** for the shot.

The local ollama HTTP wrapper exposes only one `system` slot plus one
`user` slot per call. To preserve fidelity to the upstream multi-turn
structure we:

  1. Pass the system message via the harness `system=` parameter.
  2. Concatenate the remaining turns into a single user string, each
     preceded by a clearly-marked role label so an instruction-tuned model
     can still recognise the boundaries.

`flatten(messages) -> (system, user)` returns the two halves ready for
`call_llm(model=..., system=system, prompt=user)`.
"""
from __future__ import annotations

from typing import Iterable

_LABEL = {"system": "SYSTEM:", "user": "USER:", "assistant": "ASSISTANT:"}


def flatten(messages: Iterable[dict]) -> tuple[str, str]:
    """Split an upstream-style message list into (system, user) for ollama.

    The first message is expected to be `{"role": "system", ...}` and is
    returned as the `system` half. All subsequent messages are concatenated
    with role labels so the structure of the multi-turn dialogue is
    preserved in the flattened user prompt.
    """
    msgs = list(messages)
    if not msgs:
        return "", ""
    if msgs[0]["role"] != "system":
        return "", "\n\n".join(_render(m) for m in msgs)

    system = msgs[0]["content"]
    tail = msgs[1:]
    user = "\n\n".join(_render(m) for m in tail)
    return system, user


def _render(m: dict) -> str:
    role = m.get("role", "user")
    label = _LABEL.get(role, role.upper() + ":")
    return f"{label}\n{m['content']}"


__all__ = ["flatten"]