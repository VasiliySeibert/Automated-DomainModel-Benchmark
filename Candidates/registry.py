"""Candidate registry — walks the Candidates/ tree to discover strategies.

Each prompt strategy lives in its own folder:

    Candidates/<source>/<strategy>/strategy.py

This module walks the tree, dynamically imports each `strategy.py` and
collects the `SPEC` / `register()` calls that the strategy module performs
at import time.

The registry is the single source of truth for the orchestrator:

    from Candidates.registry import all_specs, get_strategy
    for spec in all_specs():
        for model in models:
            run_strategy(spec, model, nlt)
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger(__name__)

CANDIDATES_ROOT = Path(__file__).resolve().parent

# No top-level exclusions are needed: the LLM-access layer lives
# inlined as `_ollama.py` inside each strategy folder (no shared harness
# modules exist anywhere in the repo).
EXCLUDE_TOP_DIRS: set[str] = set()
# Top-level directories that contain strategy sub-folders (NOT strategies
# themselves — they are "sources"). The `AutomatedDomainModelling_zenodo`
# folder uses underscores so it can be imported as a normal Python package.
SOURCE_DIRS = {
    "text2uml-kaiser",
    "AutomatedDomainModelling_zenodo",
    "ai4se_benchmarkPaper",
}


@dataclass
class CandidateSpec:
    """Static metadata for a prompt strategy.

    `run_fn(model, nlt) -> dict` is set by the registry after dynamic
    import. The strategy module exposes `run(spec, nlt) -> dict`; the
    registry binds `run_fn = lambda nlt: module.run(spec, nlt)`.

    The orchestrator sets `model` (full LLM tag, e.g. `glm-5.1:cloud`)
    and `model_short` before each cell invocation. The strategy's
    inlined `_ollama.py` helper handles the HTTP call.
    """
    source: str
    strategy: str
    uses_llm: bool
    skip_folders: tuple[str, ...]
    timeout: int
    description: str
    module_path: Optional[Path] = None
    run_fn: Optional[Callable] = None
    model: str = ""
    model_short: str = ""
    # Optional sampling overrides — leave None to use the harness default.
    temperature: Optional[float] = None
    num_predict: Optional[int] = None


_REGISTRY: dict[tuple[str, str], CandidateSpec] = {}


def _bind_run_fn(spec_obj: CandidateSpec, mod) -> None:
    """Attach the run_fn wrapper and module_path to the spec."""
    spec_obj.module_path = mod.__file__ if hasattr(mod, "__file__") else None
    # Note: the lambda binds `spec_obj` by default-arg, so updates to
    # spec_obj.model / spec_obj.model_short BEFORE the lambda is
    # invoked ARE visible to the strategy code.
    spec_obj.run_fn = lambda nlt, _m=mod, _s=spec_obj: _m.run(_s, nlt)


def register(spec: CandidateSpec) -> None:
    """Called by each strategy.py at import time.

    Note: does NOT set run_fn here because we don't yet have a handle
    on the strategy module. discover() will set it on the next call.
    """
    _REGISTRY[(spec.source, spec.strategy)] = spec


def _walk_strategies() -> list[tuple[Path, str, str]]:
    """Yield (strategy.py, source, strategy) tuples for every candidate."""
    for source_dir in SOURCE_DIRS:
        sp = CANDIDATES_ROOT / source_dir
        if not sp.is_dir():
            log.warning("source dir missing: %s", sp)
            continue
        for strategy_dir in sorted(p for p in sp.iterdir() if p.is_dir()):
            strat_py = strategy_dir / "strategy.py"
            if not strat_py.is_file():
                continue
            yield strat_py, source_dir, strategy_dir.name


def _import_module(name: str, path: Path, package: str | None = None):
    """Dynamic import that handles any module name (including names containing
    characters that are illegal in Python identifiers, e.g. dashes).

    If `package` is given, it is set as the loaded module's `__package__`
    attribute so that the module can use relative imports (`from ._ollama
    import …`). Without this, relative imports fail because the module
    is loaded as a top-level module.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    if package is not None:
        mod.__package__ = package
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def discover() -> int:
    """Walk the tree, import every strategy, register its SPEC.

    Re-imports every strategy.py even if its SPEC is already in
    `_REGISTRY`, so that `run_fn` is always set (the autouse pytest
    fixture relies on this).

    Returns the number of newly-loaded strategies.
    """
    loaded = 0
    for strat_py, source, strategy in _walk_strategies():
        key = (source, strategy)
        mod_name = f"_cand_{source.replace('-', '_')}_{strategy}"
        # Set the loaded module's `__package__` to its dotted path under
        # `Candidates/` so relative imports inside the strategy resolve.
        package = f"Candidates.{source}.{strategy}" if source else None
        try:
            mod = _import_module(mod_name, strat_py, package=package)
            spec_obj = getattr(mod, "SPEC", None)
            if spec_obj is None:
                log.warning("no SPEC in %s", strat_py)
                continue
            _bind_run_fn(spec_obj, mod)
            _REGISTRY[key] = spec_obj
            loaded += 1
        except Exception as exc:
            log.error("failed to load %s: %s", strat_py, exc)
    return loaded


def all_specs() -> list[CandidateSpec]:
    """Return every registered spec, sorted by (source, strategy)."""
    discover()
    return sorted(_REGISTRY.values(), key=lambda s: (s.source, s.strategy))


def specs_by_source(source: str) -> list[CandidateSpec]:
    return [s for s in all_specs() if s.source == source]


def get_strategy(source: str, strategy: str) -> Optional[CandidateSpec]:
    discover()
    return _REGISTRY.get((source, strategy))


__all__ = [
    "CandidateSpec",
    "register",
    "discover",
    "all_specs",
    "specs_by_source",
    "get_strategy",
    "CANDIDATES_ROOT",
    "SOURCE_DIRS",
]