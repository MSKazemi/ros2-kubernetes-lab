"""Static invariants for every YAML file in the repository.

Parsing uses PyYAML (``yaml.safe_load_all``); the test is skipped with a clear
message if PyYAML is not installed. Only documents with ``apiVersion`` and
``kind`` are treated as Kubernetes manifests; Helm values files and GitHub
workflow files are parsed but not checked against the workload rules.

Violations are never printed with their values: a Secret manifest sits in
MonitoringSystem/, so messages name only the file, rule and image/container.

Allowlist entries are exact (file, rule) pairs with a reason. A pair that is
no longer violated is reported as a failure too, so the list cannot go stale.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO

yaml = pytest.importorskip("yaml", reason="PyYAML is required: pip install pyyaml")

SKIP_DIRS = {".git", ".claude", ".playwright-mcp", "node_modules", "__pycache__"}
WORKLOAD_KINDS = {
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "ReplicaSet",
    "Job",
    "CronJob",
    "Pod",
}

# (repo-relative path, rule id) -> reason. Keep this list short and honest.
LEGACY = "legacy Foxy example (ROS 2 Foxy is end-of-life, see AGENTS.md); not a supported path"
ALLOWLIST: dict[tuple[str, str], str] = {
    ("ROS2/ros_one.yaml", "missing-limits:ros"): f"{LEGACY}; predates resource limits",
    (
        "ROS2/ros_one.yaml",
        "latest-tag:docker.io/kazemi/ros-foxy-with-stress-ng",
    ): f"{LEGACY}; image is untagged, so it resolves to :latest",
    (
        "ROS2/ros_dep_1.yaml",
        "latest-tag:docker.io/kazemi/ros-foxy-with-stress-ng",
    ): f"{LEGACY}; image is untagged, so it resolves to :latest",
    (
        "ROS2/ros_dep_2.yaml",
        "latest-tag:docker.io/kazemi/ros-foxy-with-stress-ng",
    ): f"{LEGACY}; image is untagged, so it resolves to :latest",
    (
        "ROS2/ros_dep_3.yaml",
        "latest-tag:docker.io/kazemi/ros-foxy-with-stress-ng",
    ): f"{LEGACY}; image is untagged, so it resolves to :latest",
    (
        "ROS2/VPA.yaml",
        "latest-tag:docker.io/kazemi/ros-foxy-with-stress-ng",
    ): f"{LEGACY}; image is untagged, so it resolves to :latest",
}


def repo_yaml_files() -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith((".yaml", ".yml")):
                found.append(Path(dirpath, name))
    return sorted(found)


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def load_documents(path: Path) -> list[object]:
    return list(yaml.safe_load_all(path.read_text(encoding="utf-8")))


def pod_spec(doc: dict[str, Any]) -> dict[str, Any] | None:
    kind = doc.get("kind")
    spec: dict[str, Any] = doc.get("spec") or {}
    if kind == "Pod":
        return spec
    if kind == "CronJob":
        job: dict[str, Any] = (spec.get("jobTemplate") or {}).get("spec") or {}
        template: dict[str, Any] = job.get("template") or {}
        return template.get("spec")
    template = spec.get("template") or {}
    return template.get("spec")


def image_is_unpinned(image: str) -> bool:
    if "@" in image:  # digest pin
        return False
    last = image.rsplit("/", 1)[-1]
    if ":" not in last:  # no tag means :latest
        return True
    return last.rsplit(":", 1)[1] == "latest"


def violations_for(path: Path) -> list[str]:
    found: list[str] = []
    for doc in load_documents(path):
        if not isinstance(doc, dict) or "kind" not in doc:
            continue
        spec = pod_spec(doc) if doc.get("kind") in WORKLOAD_KINDS else None
        if spec is None:
            continue
        for host_field in ("hostNetwork", "hostPID", "hostIPC"):
            if spec.get(host_field) is True:
                found.append(f"host-namespace:{host_field}")
        for container in (spec.get("containers") or []) + (
            spec.get("initContainers") or []
        ):
            name = container.get("name", "?")
            security = container.get("securityContext") or {}
            if security.get("privileged") is True:
                found.append(f"privileged:{name}")
            limits = (container.get("resources") or {}).get("limits") or {}
            if not limits:
                found.append(f"missing-limits:{name}")
            image = str(container.get("image", ""))
            if image_is_unpinned(image):
                found.append(f"latest-tag:{image}")
    return found


ALL_YAML = repo_yaml_files()


@pytest.mark.parametrize("path", ALL_YAML, ids=rel)
def test_yaml_parses(path: Path) -> None:
    load_documents(path)


MANIFESTS = [
    p
    for p in ALL_YAML
    if any(
        isinstance(d, dict) and "kind" in d and "apiVersion" in d
        for d in load_documents(p)
    )
]


@pytest.mark.parametrize("path", MANIFESTS, ids=rel)
def test_manifest_invariants(path: Path) -> None:
    key_prefix = rel(path)
    found = violations_for(path)
    unexpected = [v for v in found if (key_prefix, v) not in ALLOWLIST]
    assert not unexpected, (
        f"{key_prefix}: policy violations (report, do not weaken): {unexpected}"
    )


def test_allowlist_entries_are_still_needed() -> None:
    current = {(rel(p), v) for p in MANIFESTS for v in violations_for(p)}
    stale = sorted(key for key in ALLOWLIST if key not in current)
    assert not stale, f"remove fixed allowlist entries: {stale}"
    for key, reason in ALLOWLIST.items():
        assert reason.strip(), f"allowlist entry {key} needs a reason"
