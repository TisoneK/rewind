"""Shared test helpers. Layer tests import only what they need from here;
nothing in this file imports a layer module, so each layer's tests can run
on their own.
"""
from __future__ import annotations

from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def example(name: str) -> str:
    """Return the source text of an example program by file name."""
    return (EXAMPLES / name).read_text(encoding="utf-8")
