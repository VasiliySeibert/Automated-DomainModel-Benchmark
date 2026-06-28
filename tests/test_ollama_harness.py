"""Tests for the Ollama HTTP harness."""
from __future__ import annotations

import pytest
import responses

from Candidates.ollama.harness import (
    DEFAULT_HOST, DEFAULT_TIMEOUT, call, host, list_models,
)


def test_default_host():
    assert DEFAULT_HOST == "http://localhost:11434"


def test_host_no_trailing_slash():
    import os
    os.environ["OLLAMA_HOST"] = "http://example.com:11434/"
    try:
        assert host() == "http://example.com:11434"
    finally:
        del os.environ["OLLAMA_HOST"]


@responses.activate
def test_call_posts_to_chat_endpoint():
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "hello back"}},
        status=200,
    )
    out = call(model="minimax-m3:cloud", system="sys", prompt="hi")
    assert out == "hello back"
    assert len(responses.calls) == 1
    body = responses.calls[0].request.body
    assert b"minimax-m3:cloud" in body
    assert b'"role": "system"' in body
    assert b'"role": "user"' in body


@responses.activate
def test_call_without_system():
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "reply"}},
        status=200,
    )
    out = call(model="m", system="", prompt="hi")
    assert out == "reply"
    body = responses.calls[0].request.body
    assert b"system" not in body


@responses.activate
def test_list_models():
    responses.add(
        responses.GET,
        "http://localhost:11434/api/tags",
        json={"models": [{"name": "a"}, {"name": "b"}]},
        status=200,
    )
    assert list_models() == ["a", "b"]


@responses.activate
def test_call_passes_temperature_when_set():
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "ok"}},
        status=200,
    )
    call(model="m", system="", prompt="hi", temperature=0.7)
    body = responses.calls[0].request.body
    import json as _json
    payload = _json.loads(body)
    assert payload["options"]["temperature"] == 0.7


@responses.activate
def test_call_passes_num_predict_when_set():
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "ok"}},
        status=200,
    )
    call(model="m", system="", prompt="hi", num_predict=1024)
    body = responses.calls[0].request.body
    import json as _json
    payload = _json.loads(body)
    assert payload["options"]["num_predict"] == 1024


@responses.activate
def test_call_omits_options_when_unspecified():
    responses.add(
        responses.POST,
        "http://localhost:11434/api/chat",
        json={"message": {"content": "ok"}},
        status=200,
    )
    call(model="m", system="", prompt="hi")
    body = responses.calls[0].request.body
    import json as _json
    payload = _json.loads(body)
    assert "options" not in payload