"""Shared helpers for the repository's hermetic script tests.

Every test here runs offline, needs no Docker, Vagrant, VirtualBox or Kubernetes
cluster, and writes only inside pytest's ``tmp_path``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO


def run_python(
    script: Path,
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a repository script with the interpreter running the tests."""
    full_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
    }
    if env is not None:
        full_env = env
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
