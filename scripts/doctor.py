#!/usr/bin/env python3
"""Preflight check for Linux, macOS and Windows hosts (stdlib only, read-only).

Reports which lab paths this machine can realistically run and flags the problems
that most often break a first attempt:

  * CRLF line endings in files that execute inside Linux (scripts, Vagrantfile,
    Dockerfile, YAML) -- typical after a Windows checkout with core.autocrlf=true;
  * an Arm CPU (the Vagrant box is x86-64 VirtualBox only);
  * too little RAM for the three-VM lab;
  * missing Git / Vagrant / VirtualBox / Docker / kubectl.

It installs nothing and changes nothing. Exit status is 1 only for FAIL results
(for example CRLF in provisioning scripts); WARN and INFO never fail the run.

Usage:  python scripts/doctor.py [--root DIR]
        (use `py -3 scripts/doctor.py` on Windows if `python` is not on PATH)
"""

from __future__ import annotations

import argparse
import ctypes
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Total VM memory requested by the Vagrantfile profiles (MB). Keep in sync with
# the `lab_profiles` table in the Vagrantfile.
PROFILE_MB = {"default": 18240 + 2 * 6096, "small": 8192 + 2 * 4096}

# Files that run on Linux and therefore must be stored and checked out with LF.
LF_ONLY_NAMES = {"Vagrantfile", "Dockerfile"}
LF_ONLY_SUFFIXES = {".sh", ".yaml", ".yml", ".py"}

WINDOWS_TOOL_DIRS = {
    "VBoxManage": [r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"],
    "vagrant": [r"C:\HashiCorp\Vagrant\bin\vagrant.exe"],
}

results: list[tuple[str, str, str]] = []


def report(level: str, title: str, detail: str = "") -> None:
    results.append((level, title, detail))
    print(f"[{level:<4}] {title}")
    for line in detail.splitlines():
        print(f"       {line}")


def run(cmd: list[str], cwd: Path | None = None) -> str | None:
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def find_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if platform.system() == "Windows":
        for candidate in WINDOWS_TOOL_DIRS.get(name, []):
            if os.path.exists(candidate):
                return candidate
    return None


def total_ram_mb() -> int | None:
    """Total physical RAM in MB, or None if it cannot be determined."""
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) // 1024
        elif system == "Darwin":
            out = run(["sysctl", "-n", "hw.memsize"])
            return int(out) // (1024 * 1024) if out else None
        elif system == "Windows":

            class MemStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MemStatus()
            stat.dwLength = ctypes.sizeof(MemStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                return int(stat.ullTotalPhys) // (1024 * 1024)
    except (OSError, ValueError, AttributeError):
        return None
    return None


def repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path(__file__).resolve().parent
    top = run(["git", "rev-parse", "--show-toplevel"], cwd=here)
    return Path(top).resolve() if top else here.parent


def tracked_files(root: Path) -> list[Path]:
    out = run(["git", "ls-files", "-z"], cwd=root)
    if out is None:
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [root / name for name in out.split("\0") if name]


def must_be_lf(path: Path) -> bool:
    return path.name in LF_ONLY_NAMES or path.suffix in LF_ONLY_SUFFIXES


def check_platform() -> tuple[str, str]:
    system, machine = platform.system(), platform.machine().lower()
    is_arm = any(tag in machine for tag in ("arm", "aarch64"))
    release = platform.release().lower()
    report("INFO", f"Host: {system} {platform.release()} ({machine}), Python {platform.python_version()}")
    if system == "Linux" and "microsoft" in release:
        report(
            "WARN",
            "Running inside WSL 2",
            "The Docker path works well here. Run Vagrant + VirtualBox from Windows\n"
            "PowerShell instead; see docs/WINDOWS-AND-MAC.md.",
        )
    return system, "arm" if is_arm else "x86"


def check_git(root: Path) -> None:
    if not find_tool("git"):
        report("FAIL", "git not found on PATH", "Install Git, then reopen the terminal.")
        return
    autocrlf = run(["git", "config", "--get", "core.autocrlf"], cwd=root) or "(unset)"
    attrs = (root / ".gitattributes").exists()
    level = "INFO" if attrs or autocrlf in ("false", "input") else "WARN"
    report(
        level,
        f"git core.autocrlf = {autocrlf}; .gitattributes {'present' if attrs else 'MISSING'}",
        "" if attrs else "Without .gitattributes, autocrlf=true writes CRLF into the shell scripts.",
    )


def check_eol(root: Path) -> None:
    bad = []
    for path in tracked_files(root):
        if not path.is_file() or not must_be_lf(path):
            continue
        try:
            if b"\r\n" in path.read_bytes():
                bad.append(path.relative_to(root).as_posix())
        except OSError:
            continue
    if bad:
        shown = "\n".join(f"  {name}" for name in bad[:12])
        more = f"\n  ... and {len(bad) - 12} more" if len(bad) > 12 else ""
        report(
            "FAIL",
            f"{len(bad)} file(s) that run on Linux contain CRLF line endings",
            f"{shown}{more}\n"
            "Linux would fail with '/bin/bash^M: bad interpreter'. Fix, from the repo root:\n"
            "  git config core.autocrlf false\n"
            "  git rm --cached -r -q . && git reset --hard\n"
            "(this discards uncommitted changes; commit or stash first)",
        )
    else:
        report("OK", "Scripts, Vagrantfile, Dockerfile and YAML use LF line endings")


def check_resources() -> int | None:
    cpus = os.cpu_count() or 0
    ram = total_ram_mb()
    ram_text = f"{ram / 1024:.1f} GiB" if ram else "unknown"
    report("INFO", f"CPU threads: {cpus}; RAM: {ram_text}")
    return ram


def check_tools() -> dict[str, str | None]:
    tools = {name: find_tool(name) for name in ("vagrant", "VBoxManage", "docker", "kubectl", "kind")}
    for name, found in tools.items():
        report("OK" if found else "INFO", f"{name}: {found or 'not found'}")
    return tools


def verdict(arch: str, ram: int | None, tools: dict[str, str | None]) -> None:
    print("\nWhat this machine can run")
    if arch == "arm":
        report(
            "WARN",
            "Vagrant + VirtualBox lab: not supported on Arm",
            "The 'ubuntu/jammy64' box is x86-64 only. Use the Docker path.",
        )
    elif not (tools["vagrant"] and tools["VBoxManage"]):
        report("INFO", "Vagrant + VirtualBox lab: install Vagrant and VirtualBox first")
    elif ram is None:
        report("INFO", "Vagrant + VirtualBox lab: tools found, RAM unknown")
    elif ram >= PROFILE_MB["default"] + 4096:
        report("OK", "Vagrant + VirtualBox lab: enough RAM for the default profile")
    elif ram >= PROFILE_MB["small"] + 4096:
        report(
            "WARN",
            "Vagrant + VirtualBox lab: use the small profile",
            "LAB_PROFILE=small (not validated end to end); see docs/WINDOWS-AND-MAC.md.",
        )
    else:
        report("WARN", "Vagrant + VirtualBox lab: not enough RAM; use the Docker path")
    if tools["docker"]:
        report("OK", "Docker path (ROS 2 Jazzy image, container-only smoke test): docker found")
    else:
        report("INFO", "Docker path: install Docker Desktop (Windows/macOS) or Docker Engine (Linux)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", help="repository root (default: auto-detected)")
    args = parser.parse_args()

    root = repo_root(args.root)
    print(f"Repository: {root}\n")
    _, arch = check_platform()
    check_git(root)
    check_eol(root)
    ram = check_resources()
    tools = check_tools()
    verdict(arch, ram, tools)

    failed = [title for level, title, _ in results if level == "FAIL"]
    print()
    if failed:
        print(f"{len(failed)} blocking problem(s) found.")
        return 1
    print("No blocking problems found. This is a read-only check, not a test of the lab itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
