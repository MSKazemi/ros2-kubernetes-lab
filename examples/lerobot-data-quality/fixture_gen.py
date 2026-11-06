"""Deterministic generator for the committed SYNTHETIC fixtures (stdlib only).

Everything is computed from closed-form sine waves: no randomness, no real
robot, no person, no image payload (camera data is metadata only). Run:

    python3 fixture_gen.py            # (re)write fixtures/
    python3 fixture_gen.py --check    # exit 1 if committed fixtures drifted

Valid fixtures go to ``fixtures/valid/``. Each invalid fixture is a single
deliberate mutation of a valid one, and ``fixtures/expected_diagnostics.json``
records the one diagnostic code (and first path) each must produce.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dq_contract as c  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

LICENSE = "CC0-1.0"
TASK = "SYNTHETIC: move the six-joint arm along a smooth sine trajectory"


def _vec(kind: str, ep: int, i: int) -> list:
    out = []
    for j, (_, _, lo, hi) in enumerate(c.JOINTS):
        mid, amp = (lo + hi) / 2.0, 0.4 * (hi - lo) / 2.0
        phase = 0.3 * i + 0.5 * j + 0.2 * ep + (0.3 if kind == "action" else 0.0)
        out.append(round(mid + amp * math.sin(phase), 6))
    return out


def _camera(key: str, fps: int, w: int, h: int) -> dict:
    return {
        "dtype": "video",
        "shape": [h, w, 3],
        "names": list(c.CAMERA_SHAPE_NAMES),
        "camera": {
            "width": w,
            "height": h,
            "encoding": "rgb8",
            "fps": fps,
            "source": "SYNTHETIC: no pixel payload is stored in this metadata",
        },
    }


def make_valid(name: str, fps: int, lengths: list) -> dict:
    feats = {
        c.STATE_KEY: {"dtype": "float32", "shape": [c.VECTOR_DIM], "names": list(c.JOINT_NAMES), "units": list(c.JOINT_UNITS)},
        c.ACTION_KEY: {"dtype": "float32", "shape": [c.VECTOR_DIM], "names": list(c.JOINT_NAMES), "units": list(c.JOINT_UNITS)},
        "observation.images.front": _camera("front", fps, 64, 48),
        "observation.images.wrist": _camera("wrist", fps, 32, 32),
    }
    episodes, start = [], 0
    for e, n in enumerate(lengths):
        frames = [
            {
                "frame_index": i,
                "timestamp": round(i / fps, 6),
                c.STATE_KEY: _vec("state", e, i),
                c.ACTION_KEY: _vec("action", e, i),
            }
            for i in range(n)
        ]
        episodes.append(
            {
                "episode_index": e,
                "task_index": 0,
                "length": n,
                "dataset_from_index": start,
                "dataset_to_index": start + n,
                "frames": frames,
            }
        )
        start += n
    return {
        "schema_version": c.SCHEMA_VERSION,
        "synthetic": True,
        "license": LICENSE,
        "dataset_name": name,
        "generator": {"name": "fixture_gen.py", "deterministic": True, "note": "closed-form sine waves; no randomness"},
        "fps": fps,
        "timestamp_tolerance_s": c.DEFAULT_TIMESTAMP_TOLERANCE_S,
        "robot_type": "synthetic_6dof_arm",
        "source_contract": "ros2-obs-action/v1",
        "features": feats,
        "tasks": [{"task_index": 0, "task": TASK}],
        "episodes": episodes,
    }


# ------------------------------------------------------------------ invalid mutations


def _reindex(doc: dict) -> None:
    """Recompute contiguous boundaries after a structural mutation."""
    start = 0
    for ep in doc["episodes"]:
        ep["dataset_from_index"] = start
        start += len(ep["frames"])
        ep["dataset_to_index"] = start


def m_dim_frame(d):
    d["episodes"][1]["frames"][2][c.ACTION_KEY].pop()


def m_dim_feature(d):
    d["features"][c.ACTION_KEY]["shape"] = [5]


def m_unit(d):
    d["features"][c.STATE_KEY]["units"][5] = "mm"


def m_non_monotonic(d):
    f = d["episodes"][0]["frames"]
    f[3]["timestamp"] = f[2]["timestamp"] - 0.05


def m_drift(d):
    d["episodes"][1]["frames"][3]["timestamp"] = round(d["episodes"][1]["frames"][3]["timestamp"] + 0.03, 6)


def m_cam_block(d):
    del d["features"]["observation.images.wrist"]["camera"]


def m_cam_feature(d):
    del d["features"]["observation.images.front"]


def m_cam_invalid(d):
    d["features"]["observation.images.front"]["camera"]["height"] = 64  # shape says 48


def m_empty(d):
    d["episodes"][1]["frames"] = []
    d["episodes"][1]["length"] = 0
    _reindex(d)


def m_dup(d):
    d["episodes"][2]["episode_index"] = 1


def m_gap(d):
    d["episodes"][2]["episode_index"] = 3


def m_boundary(d):
    d["episodes"][2]["dataset_from_index"] += 1
    d["episodes"][2]["dataset_to_index"] += 1


def m_length(d):
    d["episodes"][0]["length"] += 1


def m_lic_missing(d):
    del d["license"]


def m_lic_bad(d):
    d["license"] = "all-rights-reserved"


def m_version(d):
    d["schema_version"] = "synthetic-episodes-meta/v9"


def m_not_synth(d):
    d["synthetic"] = False


def m_task(d):
    d["tasks"][0]["task"] = "   "


def m_limits(d):
    d["episodes"][0]["frames"][1][c.STATE_KEY][5] = 0.5


def m_fps(d):
    d["fps"] = 0


def m_frame_index(d):
    d["episodes"][0]["frames"][2]["frame_index"] = 7


# name -> (mutation, expected code, expected first path)
INVALID = {
    "dim_mismatch_frame_action": (m_dim_frame, "DIM_MISMATCH", "/episodes/1/frames/2/action"),
    "dim_mismatch_feature_shape": (m_dim_feature, "DIM_MISMATCH", "/features/action/shape"),
    "unit_mismatch": (m_unit, "UNIT_MISMATCH", "/features/observation.state/units/5"),
    "timestamp_non_monotonic": (m_non_monotonic, "TIMESTAMP_NOT_MONOTONIC", "/episodes/0/frames/3/timestamp"),
    "timestamp_fps_drift": (m_drift, "TIMESTAMP_FPS_DRIFT", "/episodes/1/frames/3/timestamp"),
    "camera_metadata_missing": (m_cam_block, "CAMERA_METADATA_MISSING", "/features/observation.images.wrist/camera"),
    "camera_feature_missing": (m_cam_feature, "CAMERA_METADATA_MISSING", "/features/observation.images.front"),
    "camera_metadata_invalid": (m_cam_invalid, "CAMERA_METADATA_INVALID", "/features/observation.images.front/shape"),
    "episode_empty": (m_empty, "EPISODE_EMPTY", "/episodes/1"),
    "episode_index_duplicate": (m_dup, "EPISODE_INDEX_DUPLICATE", "/episodes/2/episode_index"),
    "episode_index_gap": (m_gap, "EPISODE_INDEX_GAP", "/episodes/2/episode_index"),
    "episode_boundary_gap": (m_boundary, "EPISODE_BOUNDARY_GAP", "/episodes/2/dataset_from_index"),
    "episode_length_mismatch": (m_length, "EPISODE_LENGTH_MISMATCH", "/episodes/0/length"),
    "license_missing": (m_lic_missing, "LICENSE_MISSING", "/license"),
    "license_not_allowed": (m_lic_bad, "LICENSE_NOT_ALLOWED", "/license"),
    "schema_version_unknown": (m_version, "SCHEMA_VERSION_UNKNOWN", "/schema_version"),
    "not_synthetic": (m_not_synth, "NOT_SYNTHETIC", "/synthetic"),
    "task_description_blank": (m_task, "TASK_MISSING", "/tasks/0/task"),
    "value_out_of_limits": (m_limits, "OUT_OF_LIMITS", "/episodes/0/frames/1/observation.state/5"),
    "fps_invalid": (m_fps, "FPS_INVALID", "/fps"),
    "frame_index_mismatch": (m_frame_index, "FRAME_INDEX_MISMATCH", "/episodes/0/frames/2/frame_index"),
}


def build_all() -> dict:
    """Return ``{relative_path: text}`` for every generated file."""
    base = make_valid("synthetic-arm-sine-10fps", 10, [6, 5, 4])
    files = {
        "valid/synthetic_3ep_10fps.json": base,
        "valid/synthetic_2ep_30fps.json": make_valid("synthetic-arm-sine-30fps", 30, [8, 7]),
    }
    expected = {}
    for name, (mut, code, path) in INVALID.items():
        doc = copy.deepcopy(base)
        mut(doc)
        files[f"invalid/{name}.json"] = doc
        expected[f"invalid/{name}.json"] = {"code": code, "path": path}
    out = {rel: _dump(doc) for rel, doc in files.items()}
    out["expected_diagnostics.json"] = _dump(expected)
    return out


def _dump(obj) -> str:
    text = json.dumps(obj, indent=2, ensure_ascii=True)
    # keep flat arrays of scalars on one line so fixtures stay small and diff-friendly
    text = re.sub(r"\[\s+([^\[\]{}]*?)\s+\]", lambda m: "[" + re.sub(r"\s*\n\s*", " ", m.group(1)) + "]", text)
    return text + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    if any(a not in ("--check", "--write") for a in argv):
        print("usage: fixture_gen.py [--check|--write]", file=sys.stderr)
        return 2
    drift = []
    for rel, text in build_all().items():
        path = os.path.join(FIX, rel)
        if check:
            try:
                with open(path, encoding="utf-8") as fh:
                    if fh.read() != text:
                        drift.append(rel)
            except OSError:
                drift.append(rel)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
    if check:
        for rel in drift:
            print(f"DRIFT: fixtures/{rel}", file=sys.stderr)
        print("fixtures up to date" if not drift else f"{len(drift)} fixture(s) drifted; run fixture_gen.py")
        return 1 if drift else 0
    print(f"wrote fixtures under {FIX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
