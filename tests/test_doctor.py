"""Tests for scripts/doctor.py (read-only preflight).

Tools are simulated by controlling PATH: a bin directory that holds only a
symlink to the real git, so vagrant/VBoxManage/docker/kubectl/kind are "missing".
The fixture repository and HOME live in tmp_path, so the user's global git
configuration cannot influence the result.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import SCRIPTS, run_python, write

DOCTOR = SCRIPTS / "doctor.py"
SECRET_MARKER = "DOCTOR-TEST-SECRET-MARKER-7c1e"


def git_bin() -> str:
    found = shutil.which("git")
    if not found:
        pytest.skip("git is required for the doctor tests")
    return found


def make_bin(tmp_path: Path, *, with_git: bool) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if with_git:
        (bin_dir / "git").symlink_to(git_bin())
    return bin_dir


def hermetic_env(tmp_path: Path, bin_dir: Path) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return {
        "PATH": str(bin_dir),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
        "GIT_TEMPLATE_DIR": str(home / "empty-template"),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        # Canary: doctor must never echo environment values.
        "DOCTOR_TEST_CANARY": SECRET_MARKER,
    }


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        [git_bin(), *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(repo.parent),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(repo.parent / "none"),
            "GIT_TEMPLATE_DIR": str(repo.parent / "empty-template"),
        },
    )


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    write(repo / "scripts" / "setup.sh", "#!/bin/bash\necho ok\n")
    write(repo / "Vagrantfile", "Vagrant.configure('2') do |c|\nend\n")
    write(repo / "README.md", "# fixture\r\n")  # CRLF is allowed outside LF-only files
    git(repo, "add", "-A")
    return repo


def doctor(
    tmp_path: Path, repo: Path, *, with_git: bool = True
) -> subprocess.CompletedProcess[str]:
    bin_dir = make_bin(tmp_path, with_git=with_git)
    return run_python(DOCTOR, "--root", str(repo), env=hermetic_env(tmp_path, bin_dir))


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    } | {"<index>": (root / ".git" / "index").read_bytes()}


def test_missing_git_is_blocking(tmp_path: Path, fixture_repo: Path) -> None:
    result = doctor(tmp_path, fixture_repo, with_git=False)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "git not found on PATH" in result.stdout
    assert "blocking problem" in result.stdout


def test_clean_repo_with_only_git_on_path_passes(
    tmp_path: Path, fixture_repo: Path
) -> None:
    result = doctor(tmp_path, fixture_repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        "[OK  ] Scripts, Vagrantfile, Dockerfile and YAML use LF line endings"
        in result.stdout
    )
    assert "vagrant: not found" in result.stdout
    assert "No blocking problems found." in result.stdout


def test_crlf_in_linux_script_is_blocking(tmp_path: Path, fixture_repo: Path) -> None:
    (fixture_repo / "scripts" / "setup.sh").write_bytes(b"#!/bin/bash\r\necho ok\r\n")
    git(fixture_repo, "add", "-A")
    result = doctor(tmp_path, fixture_repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 file(s) that run on Linux contain CRLF" in result.stdout
    assert "scripts/setup.sh" in result.stdout


def test_crlf_in_markdown_is_not_blocking(tmp_path: Path, fixture_repo: Path) -> None:
    # fixture_repo already commits README.md with CRLF; it must not fail the run.
    result = doctor(tmp_path, fixture_repo)
    assert result.returncode == 0
    assert "README.md" not in result.stdout


def test_doctor_is_read_only_and_never_prints_environment(
    tmp_path: Path, fixture_repo: Path
) -> None:
    (fixture_repo / "scripts" / "setup.sh").write_bytes(b"#!/bin/bash\r\n")
    git(fixture_repo, "add", "-A")
    before = snapshot(fixture_repo)
    result = doctor(tmp_path, fixture_repo)
    after = snapshot(fixture_repo)
    assert result.returncode == 1
    assert before == after, "doctor must not modify the repository or its index"
    combined = result.stdout + result.stderr
    assert SECRET_MARKER not in combined
    assert "DOCTOR_TEST_CANARY" not in combined


def test_doctor_runs_in_repo_without_git_metadata(tmp_path: Path) -> None:
    """Without git the script falls back to scanning the directory tree."""
    plain = tmp_path / "plain"
    write(plain / "run.sh", "#!/bin/bash\r\n")
    result = doctor(tmp_path, plain, with_git=False)
    assert result.returncode == 1
    assert "run.sh" in result.stdout
