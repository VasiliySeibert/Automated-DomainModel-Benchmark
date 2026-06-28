"""Tests for the per-strategy Ollama HTTP wrapper.

Each LLM-driven strategy has its own copy of `_ollama.py` (byte-identical
across all 10 strategy folders) — see `Candidates/text2uml-kaiser/zero_shot/_ollama.py`
for the canonical version. We test one canonical copy here via
`importlib.util` (the folder name `text2uml-kaiser` contains a hyphen
so it can't appear in dotted import syntax); the rest are guaranteed
identical by the build process.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import responses


_REPO_ROOT = Path(__file__).resolve().parent.parent
_OLLAMA_PATH = _REPO_ROOT / "Candidates" / "text2uml-kaiser" / "zero_shot" / "_ollama.py"


def _load_ollama():
    """Dynamically load `_ollama.py` from the zero_shot folder (the canonical copy)."""
    spec = importlib.util.spec_from_file_location("_canonical_ollama", _OLLAMA_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ollama():
    return _load_ollama()


def test_default_host(ollama):
    assert ollama.DEFAULT_HOST == "http://localhost:11434"


def test_host_no_trailing_slash(ollama):
    import os
    os.environ["OLLAMA_HOST"] = "http://example.com:11434/"
    try:
        assert ollama.host() == "http://example.com:11434"
    finally:
        del os.environ["OLLAMA_HOST"]


@responses.activate
def test_call_posts_to_chat_endpoint(ollama):
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "hello back"}},
        status=200,
    )
    out = ollama.call(model="minimax-m3:cloud", system="sys", prompt="hi")
    assert out == "hello back"
    assert len(responses.calls) == 1
    body = responses.calls[0].request.body
    assert b"minimax-m3:cloud" in body
    assert b'"role": "system"' in body
    assert b'"role": "user"' in body


@responses.activate
def test_call_without_system(ollama):
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "reply"}},
        status=200,
    )
    out = ollama.call(model="m", system="", prompt="hi")
    assert out == "reply"
    body = responses.calls[0].request.body
    assert b"system" not in body


@responses.activate
def test_call_passes_temperature_when_set(ollama):
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "ok"}},
        status=200,
    )
    ollama.call(model="m", system="", prompt="hi", temperature=0.7)
    body = responses.calls[0].request.body
    payload = json.loads(body)
    assert payload["options"]["temperature"] == 0.7


@responses.activate
def test_call_passes_num_predict_when_set(ollama):
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "ok"}},
        status=200,
    )
    ollama.call(model="m", system="", prompt="hi", num_predict=1024)
    body = responses.calls[0].request.body
    payload = json.loads(body)
    assert payload["options"]["num_predict"] == 1024


@responses.activate
def test_call_omits_options_when_unspecified(ollama):
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "ok"}},
        status=200,
    )
    ollama.call(model="m", system="", prompt="hi")
    body = responses.calls[0].request.body
    payload = json.loads(body)
    assert "options" not in payload


def test_all_10_inlined_ollama_copies_are_byte_identical():
    """All 10 per-strategy _ollama.py copies must be byte-identical so that
    bug fixes only require one update."""
    paths = [
        "Candidates/text2uml-kaiser/zero_shot/_ollama.py",
        "Candidates/text2uml-kaiser/one_shot/_ollama.py",
        "Candidates/text2uml-kaiser/few_shot/_ollama.py",
        "Candidates/text2uml-kaiser/cot/_ollama.py",
        "Candidates/text2uml-kaiser/cot_domain/_ollama.py",
        "Candidates/AutomatedDomainModelling_zenodo/zero_shot/_ollama.py",
        "Candidates/AutomatedDomainModelling_zenodo/one_shot_btms/_ollama.py",
        "Candidates/AutomatedDomainModelling_zenodo/one_shot_h2s_short/_ollama.py",
        "Candidates/AutomatedDomainModelling_zenodo/two_shot/_ollama.py",
        "Candidates/AutomatedDomainModelling_zenodo/cot/_ollama.py",
    ]
    canonical = (_REPO_ROOT / paths[0]).read_bytes()
    for p in paths[1:]:
        body = (_REPO_ROOT / p).read_bytes()
        assert body == canonical, f"{p} differs from {paths[0]}"