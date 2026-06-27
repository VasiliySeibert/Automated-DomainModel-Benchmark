# Ollama harness

Direct HTTP wrapper around the local Ollama server's `/api/chat`
endpoint. This is the **default harness** for every LLM-driven
prompt strategy in this benchmark.

## Why direct HTTP and not `opencode run`?

- No subprocess overhead.
- No "system prompt" CLI-flag workaround needed — opencode's `--prompt`
  flag is for BASIC AUTH, not for system messages.
- Direct control over the message structure (system + user turns).
- The orchestrator runs serially; HTTP latency is lower than opencode's
  detached-mode overhead.

## Usage from a strategy

```python
from Candidates.ollama.harness import call

raw = call(
    model="minimax-m3:cloud",
    system="You are a UML class-diagram emitter...",
    prompt="<specification text>",
    timeout=600,
)
```

## Configuration

| Env var       | Default                  | Notes                                    |
|---------------|--------------------------|------------------------------------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Override if Ollama runs on another host. |

## Health check

```python
from Candidates.ollama.harness import is_available, list_models

if is_available():
    print(list_models())
```

## Why a separate `opencode` candidate?

`opencode` IS still in the benchmark — it's just not used by default.
It's exposed as a candidate (see `Candidates/opencode/`) that anyone
can swap in by editing one import line in a strategy. The decision
to make Ollama the default is purely about latency: every test run
we did showed `ollama` 2-3× faster than `opencode run` on the same
model.