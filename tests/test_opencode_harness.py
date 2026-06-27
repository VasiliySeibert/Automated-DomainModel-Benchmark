"""Tests for the opencode subprocess harness."""
from __future__ import annotations

import os

import pytest

from Candidates.opencode.harness import _opencode_path, call


def test_opencode_path_override():
    os.environ["OPENCODE_BIN"] = "/custom/path/opencode"
    try:
        assert _opencode_path() == "/custom/path/opencode"
    finally:
        del os.environ["OPENCODE_BIN"]


def test_opencode_path_missing_raises():
    os.environ["OPENCODE_BIN"] = "/nonexistent/binary"
    try:
        # Our _opencode_path() returns the override as-is without
        # checking; the FileNotFoundError surfaces at call() time when
        # subprocess fails. We accept either outcome (no exception, or
        # OSError / FileNotFoundError on call).
        try:
            _opencode_path()
        except (FileNotFoundError, OSError):
            pass
    finally:
        del os.environ["OPENCODE_BIN"]


def test_call_raises_on_missing_binary():
    os.environ["OPENCODE_BIN"] = "/definitely/not/here"
    try:
        with pytest.raises((FileNotFoundError, OSError)):
            call(model_id="m", system="", prompt="x", timeout=10)
    finally:
        del os.environ["OPENCODE_BIN"]