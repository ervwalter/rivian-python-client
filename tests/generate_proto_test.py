"""Tests for deterministic protobuf generation."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_generated_protobuf_modules_are_current() -> None:
    """The checked-in modules must match the canonical local schema."""
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_proto.py"), "--check"],
        cwd=root,
        check=True,
    )
