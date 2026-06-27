# opencode harness

Subprocess wrapper around the `opencode run` non-interactive subcommand.

## Why a separate harness?

Each prompt-strategy candidate in this benchmark imports a harness at
the top of its `strategy.py`:

```python
# Default — uses direct Ollama HTTP API
from Candidates.ollama.harness import call as call_llm

# Alternative — shells out to `opencode run`
# from Candidates.opencode.harness import call as call_llm
```

The default is the Ollama direct-HTTP harness because it is 2-3× faster
than `opencode run` on the same model (no subprocess overhead, no
"system prompt" CLI-flag workaround needed).

`opencode` is included as a candidate for two reasons:

1. **Reuse** — the original implementation in `text2uml-kaiser` runs
   through LangChain + opencode, and we keep that path open for users
   who already have opencode installed and configured.
2. **Comparison** — a future ablation can flip the import line and run
   the same prompts through both harnesses to measure the overhead.

## Usage from a strategy

```python
from Candidates.opencode.harness import call

raw = call(
    model_id="ollama/minimax-m3:cloud",
    system="You are a UML class-diagram emitter...",
    prompt="<specification text>",
    timeout=600,
)
```

Note: the `model_id` parameter expects the **opencode model id**
(`provider/model:tag` format, e.g. `ollama/minimax-m3:cloud`), not the
Ollama model tag (`minimax-m3:cloud`).

## Why is this a "candidate"?

The user explicitly requested that the opencode harness be its own
candidate folder rather than a shared utility. The folder exists for
transparency and to keep the option of running prompts through opencode
open without changing any shared infrastructure.