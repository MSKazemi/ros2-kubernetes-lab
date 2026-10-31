#!/usr/bin/env python3
"""Validate the repository's Kubernetes YAML manifests against pinned API schemas.

This is a STATIC schema check. It needs no cluster, no kubeconfig and no
credentials. It does NOT prove that a workload schedules, pulls its image,
starts, or that ROS 2/DDS traffic flows between nodes.

How it works
  * Runs `kubeconform` (pinned release, SHA-256 verified on download) in strict
    mode against the built-in Kubernetes API schemas for one pinned Kubernetes
    version, fetched from a pinned commit of yannh/kubernetes-json-schema.
  * Multi-document YAML files are handled natively by kubeconform.
  * `-ignore-missing-schemas` is deliberately NOT used, because it would report
    unknown custom resources (for example the VerticalPodAutoscaler) as passing.
    Instead every exception is listed, with a reason, in
    scripts/k8s-manifests-known-issues.txt and is printed as NOT VALIDATED.
  * Helm values files are not Kubernetes manifests; they are excluded in the
    same allowlist file. There are no Helm charts or Kustomize overlays in this
    repository.

Usage
  python3 scripts/validate-k8s-manifests.py                 # all tracked manifests
  python3 scripts/validate-k8s-manifests.py path/to/a.yaml  # only these files
  python3 scripts/validate-k8s-manifests.py --kubeconform /path/to/kubeconform

Exit status: 0 = every manifest is valid or explicitly allowlisted; 1 = a
manifest failed validation or the tool could not run; 2 = bad allowlist/usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

# --- Pins -----------------------------------------------------------------
# kubeconform release v0.8.0 (published 2026-06-04). SHA-256 values are copied
# from the CHECKSUMS asset of that release:
#   https://github.com/yannh/kubeconform/releases/download/v0.8.0/CHECKSUMS
KUBECONFORM_VERSION = "v0.8.0"
KUBECONFORM_SHA256 = {
    "linux-amd64": "9bc2bffbf71f261128533edaf912153948b7ff238f9a531ae6d34466ec287883",
    "linux-arm64": "1f53fc8e81258197a35e8603054162a5af1de8c5af13746c71ab680d9534ed87",
    "darwin-amd64": "71dbc87ac9f24099a62b93570e65aa06312ba6ac8aea63b7f86e9d999edf5a92",
    "darwin-arm64": "f84f4dfbebf4a6b0b230385fa065a39ea35e02608c2b50d025dcf64775a69d67",
}
RELEASE_URL = "https://github.com/yannh/kubeconform/releases/download/{v}/kubeconform-{plat}.tar.gz"

# The lab installs Kubernetes v1.29 packages (KubernetesClusterSetup/kubeadm_kubelet_kubectl.sh).
KUBERNETES_VERSION = "1.29.0"
# Commit of https://github.com/yannh/kubernetes-json-schema (fetched 2026-10-28).
SCHEMA_COMMIT = "89a35a5e9a1412a692a2603d79c3786f602238a4"
SCHEMA_LOCATION = (
    "https://raw.githubusercontent.com/yannh/kubernetes-json-schema/"
    + SCHEMA_COMMIT
    + "/{{.NormalizedKubernetesVersion}}-standalone{{.StrictSuffix}}/"
    + "{{.ResourceKind}}{{.KindSuffix}}.json"
)

# Directories that hold Kubernetes manifests. Other YAML (.github workflows,
# issue forms, the Pages site) is intentionally out of scope.
SCAN_ROOTS = ("ROS2", "MonitoringSystem", "Network", "KubernetesClusterSetup", "kind")

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ALLOWLIST = REPO / "scripts" / "k8s-manifests-known-issues.txt"
MISSING_SCHEMA = "could not find schema"


def platform_key() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(machine)
    key = f"{system}-{arch}"
    if key not in KUBECONFORM_SHA256:
        sys.exit(f"error: no pinned kubeconform checksum for {key}; pass --kubeconform PATH ({KUBECONFORM_VERSION}).")
    return key


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_kubeconform() -> Path:
    """Download the pinned release, verify its SHA-256, and return the binary path."""
    key = platform_key()
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ros2-k8s-lab" / f"kubeconform-{KUBECONFORM_VERSION}-{key}"
    binary = cache / "kubeconform"
    if binary.is_file() and os.access(binary, os.X_OK):
        return binary
    url = RELEASE_URL.format(v=KUBECONFORM_VERSION, plat=key)
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as tmp:
        archive = Path(tmp) / "kubeconform.tar.gz"
        print(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as out:  # noqa: S310 (https, fixed host)
            shutil.copyfileobj(response, out)
        actual = sha256_of(archive)
        expected = KUBECONFORM_SHA256[key]
        if actual != expected:
            sys.exit(f"error: SHA-256 mismatch for {url}\n  expected {expected}\n  actual   {actual}")
        print(f"SHA-256 verified: {actual}")
        with tarfile.open(archive) as tar:
            member = tar.getmember("kubeconform")
            if not member.isfile():
                sys.exit("error: unexpected archive layout")
            source = tar.extractfile(member)
            assert source is not None
            staged = Path(tmp) / "kubeconform"
            with staged.open("wb") as out:
                shutil.copyfileobj(source, out)
        staged.chmod(0o755)
        staged.replace(binary)
    return binary


def resolve_kubeconform(explicit: str | None) -> Path:
    chosen = explicit or os.environ.get("KUBECONFORM")
    binary = Path(chosen) if chosen else download_kubeconform()
    try:
        version = subprocess.run([str(binary), "-v"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f"error: cannot run {binary}: {exc}")
    if version != KUBECONFORM_VERSION:
        sys.exit(f"error: {binary} reports {version!r}, but this repository pins {KUBECONFORM_VERSION}.")
    return binary


def load_allowlist(path: Path) -> dict[tuple[str, str], str]:
    """Parse `<path>:<Kind|*> -- <reason>` lines. `*` excludes the whole file."""
    entries: dict[tuple[str, str], str] = {}
    if not path.is_file():
        return entries
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        target, sep, reason = line.partition(" -- ")
        file_part, colon, kind = target.rpartition(":")
        if not (sep and colon and file_part and kind and reason.strip()):
            print(f"{path.name}:{number}: expected '<path>:<Kind|*> -- <reason>'", file=sys.stderr)
            sys.exit(2)
        entries[(file_part.strip(), kind.strip())] = reason.strip()
    return entries


def discover() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", *[f"{root}/**" for root in SCAN_ROOTS]],
            cwd=REPO, capture_output=True, check=True,
        ).stdout.decode()
        names = [n for n in out.split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        names = [str(p.relative_to(REPO)) for root in SCAN_ROOTS for p in (REPO / root).rglob("*") if p.is_file()]
    return sorted(n for n in names if n.endswith((".yaml", ".yml")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="manifest files to check (default: every tracked manifest)")
    parser.add_argument("--kubeconform", help=f"path to a kubeconform {KUBECONFORM_VERSION} binary (default: download and verify)")
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST, help="known-issues file")
    args = parser.parse_args()

    allow = load_allowlist(args.allowlist)
    explicit = bool(args.files)
    candidates = [str(Path(f)) for f in args.files] if explicit else discover()
    if not candidates:
        print("error: no manifests found", file=sys.stderr)
        return 1

    skipped = {f: allow[(f, "*")] for f in candidates if (f, "*") in allow}
    targets = [f for f in candidates if f not in skipped]

    binary = resolve_kubeconform(args.kubeconform)
    print(f"kubeconform {KUBECONFORM_VERSION}, Kubernetes {KUBERNETES_VERSION}, strict, schemas @ {SCHEMA_COMMIT[:12]}")

    results: list[dict] = []
    tool_exit = 0
    if targets:
        proc = subprocess.run(
            [str(binary), "-kubernetes-version", KUBERNETES_VERSION, "-strict", "-verbose", "-summary",
             "-output", "json", "-schema-location", SCHEMA_LOCATION, *targets],
            cwd=None if explicit else REPO, capture_output=True, text=True,
        )
        tool_exit = proc.returncode
        try:
            results = json.loads(proc.stdout).get("resources", [])
        except json.JSONDecodeError:
            print("error: could not parse kubeconform output", file=sys.stderr)
            print(proc.stdout, proc.stderr, sep="\n", file=sys.stderr)
            return 1

    failures: list[str] = []
    per_file: dict[str, list[str]] = {f: [] for f in targets}
    used: set[tuple[str, str]] = {(f, "*") for f in skipped}
    for res in results:
        fname, kind, name = res.get("filename", "?"), res.get("kind", "?"), res.get("name", "?")
        label = f"{kind}/{name or '(unnamed)'}"
        status, msg = res.get("status", ""), res.get("msg", "")
        if status == "statusValid":
            per_file.setdefault(fname, []).append(f"ok        {label}")
        elif status == "statusError" and MISSING_SCHEMA in msg and (fname, kind) in allow:
            used.add((fname, kind))
            per_file.setdefault(fname, []).append(f"UNCHECKED {label} (no schema; allowlisted)")
        else:
            per_file.setdefault(fname, []).append(f"FAIL      {label}: {msg}")
            failures.append(f"{fname}: {label}: {msg}")

    print()
    for fname in targets:
        rows = per_file.get(fname) or ["FAIL      no resources reported"]
        if not per_file.get(fname):
            failures.append(f"{fname}: no resources reported")
        print(fname)
        for row in rows:
            print(f"  {row}")
    unchecked = [(f, k) for (f, k) in sorted(used) if k != "*"]
    if skipped or unchecked:
        print("\nNOT VALIDATED (see scripts/k8s-manifests-known-issues.txt):")
        for fname, reason in sorted(skipped.items()):
            print(f"  {fname} [whole file excluded]: {reason}")
        for fname, kind in unchecked:
            print(f"  {fname} [{kind}]: {allow[(fname, kind)]}")
    if not explicit:
        for key in sorted(set(allow) - used):
            print(f"warning: stale allowlist entry {key[0]}:{key[1]} (no longer needed; remove it)", file=sys.stderr)

    valid = sum(1 for rows in per_file.values() for r in rows if r.startswith("ok "))
    print(f"\n{valid} resources valid, {len(failures)} failed, {len(unchecked)} unchecked (allowlisted), {len(skipped)} files excluded.")
    print("STATIC schema check only: this does not prove any workload runs or that ROS 2/DDS works across nodes.")
    if failures:
        print("\nFAILED:", *failures, sep="\n  ", file=sys.stderr)
        return 1
    if tool_exit not in (0, 1):
        print(f"error: kubeconform exited with {tool_exit}", file=sys.stderr)
        return 1
    if tool_exit == 1 and not unchecked:
        print("error: kubeconform failed without a reported resource error", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
