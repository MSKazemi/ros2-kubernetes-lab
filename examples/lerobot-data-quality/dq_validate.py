"""Validator and CLI for synthetic-episode metadata, contract ``synthetic-episodes-meta/v1``.

Python standard library only. Offline. Fail closed: every problem becomes a
``Diagnostic`` (stable ``code``, JSON-pointer ``path``, ``message``, ``hint``);
the ``validate_*`` functions never raise on bad input, and an unexpected
internal error becomes ``INTERNAL_ERROR`` (the document is then invalid).

This checks *metadata and tiny numeric frames of SYNTHETIC episodes*. It does
not import or call LeRobot, does not write a LeRobotDataset and does not prove
that a Hugging Face upload or reload would succeed.

CLI exit codes: 0 all files valid, 1 at least one invalid, 2 usage or I/O error.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional

# Make `python3 -I dq_validate.py` work: add only this file's own directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dq_contract as c  # noqa: E402


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str
    hint: str
    severity: str = "error"

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "hint": self.hint,
        }


def _ptr(*parts: Any) -> str:
    """Build an RFC 6901 JSON pointer."""
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


class _Collector:
    def __init__(self) -> None:
        self.items: list[Diagnostic] = []
        self.truncated = False

    def add(self, code: str, path: str, message: str, hint: Optional[str] = None) -> None:
        if len(self.items) >= c.MAX_DIAGNOSTICS:
            self.truncated = True
            return
        self.items.append(Diagnostic(code, path, message, hint or c.CODES[code][1]))


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _finite(v: Any) -> bool:
    """True for a finite real number. Huge ints (not representable as float) are not finite."""
    try:
        return math.isfinite(v)
    except OverflowError:
        return False


# --------------------------------------------------------------------------- checks


def _check_license(doc: dict, out: _Collector) -> None:
    lic = doc.get("license")
    if lic is None or (isinstance(lic, str) and not lic.strip()):
        out.add("LICENSE_MISSING", "/license", "license is absent or empty")
    elif not isinstance(lic, str):
        out.add("WRONG_TYPE", "/license", "license must be a string (SPDX id)")
    elif lic not in c.ALLOWED_LICENSES:
        out.add("LICENSE_NOT_ALLOWED", "/license", f"license {lic!r} is not allowed; allowed: {', '.join(c.ALLOWED_LICENSES)}")


def _check_fps(doc: dict, out: _Collector) -> Optional[int]:
    fps = doc.get("fps")
    if not _is_int(fps) or not 1 <= fps <= c.MAX_FPS:
        out.add("FPS_INVALID", "/fps", f"fps must be an integer in 1..{c.MAX_FPS}, got {fps!r}")
        return None
    return fps


def _check_tolerance(doc: dict, fps: Optional[int], out: _Collector) -> float:
    if "timestamp_tolerance_s" not in doc:
        return c.DEFAULT_TIMESTAMP_TOLERANCE_S
    tol = doc["timestamp_tolerance_s"]
    limit = 0.5 / fps if fps else float("inf")
    if not _is_num(tol) or not _finite(tol) or tol <= 0 or tol >= limit:
        out.add("TOLERANCE_INVALID", "/timestamp_tolerance_s", f"must be a number in (0, {limit:.6g}), got {tol!r}")
        return c.DEFAULT_TIMESTAMP_TOLERANCE_S
    return float(tol)


def _check_tasks(doc: dict, out: _Collector) -> set:
    tasks = doc.get("tasks")
    ids: set = set()
    if not isinstance(tasks, list) or not tasks:
        out.add("TASK_MISSING", "/tasks", "tasks must be a non-empty list of {task_index, task}")
        return ids
    for i, t in enumerate(tasks):
        p = _ptr("tasks", i)
        if not isinstance(t, dict):
            out.add("WRONG_TYPE", p, "task entry must be an object")
            continue
        ti, text = t.get("task_index"), t.get("task")
        if not _is_int(ti):
            out.add("WRONG_TYPE" if "task_index" in t else "TASK_MISSING", p + "/task_index", f"task_index must be an integer >= 0, got {ti!r}")
        elif ti < 0:
            out.add("TASK_MISSING", p + "/task_index", "task_index must be an integer >= 0")
        elif ti in ids:
            out.add("TASK_MISSING", p + "/task_index", f"duplicate task_index {ti}")
        else:
            ids.add(ti)
        if "task" in t and not isinstance(text, str):
            out.add("WRONG_TYPE", p + "/task", f"task description must be a string, got {text!r}")
        elif not isinstance(text, str) or not text.strip():
            out.add("TASK_MISSING", p + "/task", "task description must be a non-empty string")
    return ids


def _check_vector_feature(feats: dict, key: str, out: _Collector) -> None:
    base = _ptr("features", key)
    feat = feats.get(key)
    if feat is None:
        out.add("FEATURE_MISSING", base, f"required feature {key!r} is not declared")
        return
    if not isinstance(feat, dict):
        out.add("WRONG_TYPE", base, "feature must be an object")
        return
    if "dtype" in feat and not isinstance(feat["dtype"], str):
        out.add("WRONG_TYPE", base + "/dtype", f"dtype must be a string, got {feat['dtype']!r}")
    elif feat.get("dtype") != c.VECTOR_DTYPE:
        out.add("FEATURE_DTYPE_BAD", base + "/dtype", f"dtype must be {c.VECTOR_DTYPE!r}, got {feat.get('dtype')!r}")
    shape = feat.get("shape")
    if not (isinstance(shape, list) and len(shape) == 1 and _is_int(shape[0])):
        out.add("FEATURE_SHAPE_BAD", base + "/shape", f"shape must be [{c.VECTOR_DIM}], got {shape!r}")
    elif shape[0] != c.VECTOR_DIM:
        out.add("DIM_MISMATCH", base + "/shape", f"shape declares {shape[0]} values, contract requires {c.VECTOR_DIM}")
    names = feat.get("names")
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        out.add("WRONG_TYPE" if "names" in feat else "MISSING_FIELD", base + "/names", f"names must be a list of strings, got {names!r}")
    elif len(names) != c.VECTOR_DIM:
        out.add("DIM_MISMATCH", base + "/names", f"{len(names)} names, contract requires {c.VECTOR_DIM}")
    elif tuple(names) != c.JOINT_NAMES:
        out.add("FEATURE_NAMES_MISMATCH", base + "/names", f"expected {list(c.JOINT_NAMES)}, got {names}")
    units = feat.get("units")
    if units is None:
        out.add("MISSING_FIELD", base + "/units", "units are required for every vector feature")
    elif not isinstance(units, list):
        out.add("WRONG_TYPE", base + "/units", "units must be a list of strings")
    elif len(units) != c.VECTOR_DIM:
        out.add("DIM_MISMATCH", base + "/units", f"{len(units)} units, contract requires {c.VECTOR_DIM}")
    else:
        for j, (got, want) in enumerate(zip(units, c.JOINT_UNITS)):
            if not isinstance(got, str):
                out.add("WRONG_TYPE", base + f"/units/{j}", f"unit must be a string, got {got!r}")
            elif got != want:
                out.add("UNIT_MISMATCH", base + f"/units/{j}", f"{c.JOINT_NAMES[j]}: unit {got!r}, contract requires {want!r}")


def _check_camera_feature(feats: dict, key: str, fps: Optional[int], out: _Collector, required: bool) -> None:
    base = _ptr("features", key)
    feat = feats.get(key)
    if feat is None:
        if required:
            out.add("CAMERA_METADATA_MISSING", base, f"required camera feature {key!r} is not declared")
        return
    if not isinstance(feat, dict):
        out.add("WRONG_TYPE", base, "feature must be an object")
        return
    if "dtype" in feat and not isinstance(feat["dtype"], str):
        out.add("WRONG_TYPE", base + "/dtype", f"dtype must be a string, got {feat['dtype']!r}")
    elif feat.get("dtype") not in c.CAMERA_DTYPES:
        out.add("FEATURE_DTYPE_BAD", base + "/dtype", f"dtype must be one of {list(c.CAMERA_DTYPES)}, got {feat.get('dtype')!r}")
    if feat.get("names") != c.CAMERA_SHAPE_NAMES:
        out.add("FEATURE_NAMES_MISMATCH", base + "/names", f"names must be {c.CAMERA_SHAPE_NAMES}, got {feat.get('names')!r}")
    cam = feat.get("camera")
    if "camera" in feat and not isinstance(cam, dict):
        out.add("WRONG_TYPE", base + "/camera", f"camera metadata must be an object, got {cam!r}")
        return
    if cam is None:
        out.add("CAMERA_METADATA_MISSING", base + "/camera", "camera metadata block (width, height, encoding, fps) is missing")
        return
    absent = [f for f in c.CAMERA_REQUIRED_FIELDS if f not in cam]
    for f in absent:
        out.add("CAMERA_METADATA_MISSING", base + "/camera/" + f, f"camera.{f} is missing")
    w, h, enc, cfps = cam.get("width"), cam.get("height"), cam.get("encoding"), cam.get("fps")
    good = True
    for name, v in (("width", w), ("height", h)):
        if name in absent:
            continue
        if not _is_int(v):
            out.add("WRONG_TYPE", base + "/camera/" + name, f"{name} must be an integer, got {v!r}")
            good = False
        elif not 1 <= v <= c.MAX_CAMERA_DIM:
            out.add("CAMERA_METADATA_INVALID", base + "/camera/" + name, f"{name} must be in 1..{c.MAX_CAMERA_DIM}, got {v!r}")
            good = False
    if "encoding" not in absent:
        # type-check BEFORE the dict lookup: lists/dicts are unhashable
        if not isinstance(enc, str):
            out.add("WRONG_TYPE", base + "/camera/encoding", f"encoding must be a string, got {enc!r}")
            good = False
        elif enc not in c.CAMERA_ENCODINGS:
            out.add("CAMERA_METADATA_INVALID", base + "/camera/encoding", f"encoding must be one of {sorted(c.CAMERA_ENCODINGS)}, got {enc!r}")
            good = False
    if "fps" not in absent:
        if not _is_int(cfps):
            out.add("WRONG_TYPE", base + "/camera/fps", f"fps must be an integer, got {cfps!r}")
        elif fps is not None and cfps != fps:
            out.add("CAMERA_METADATA_INVALID", base + "/camera/fps", f"camera fps {cfps!r} differs from dataset fps {fps}")
    shape = feat.get("shape")
    if not (isinstance(shape, list) and len(shape) == 3 and all(_is_int(s) for s in shape)):
        out.add("FEATURE_SHAPE_BAD", base + "/shape", f"shape must be [height, width, channels], got {shape!r}")
    elif good and not absent:
        want = [h, w, c.CAMERA_ENCODINGS[enc]]
        if shape != want:
            out.add("CAMERA_METADATA_INVALID", base + "/shape", f"shape {shape} disagrees with camera metadata, expected {want}")


def _check_features(doc: dict, fps: Optional[int], out: _Collector) -> None:
    feats = doc.get("features")
    if not isinstance(feats, dict) or not feats:
        out.add("FEATURE_MISSING", "/features", "features must be a non-empty object")
        return
    for key in c.VECTOR_FEATURES:
        _check_vector_feature(feats, key, out)
    for key in c.REQUIRED_CAMERA_KEYS:
        _check_camera_feature(feats, key, fps, out, required=True)
    for key in feats:
        if key.startswith(c.CAMERA_PREFIX) and key not in c.REQUIRED_CAMERA_KEYS:
            _check_camera_feature(feats, key, fps, out, required=False)


def _check_vector(frame: dict, key: str, p: str, out: _Collector) -> None:
    vec = frame.get(key)
    path = p + "/" + key
    if not isinstance(vec, list):
        out.add("WRONG_TYPE" if key in frame else "MISSING_FIELD", path, f"{key} must be a list of {c.VECTOR_DIM} numbers")
        return
    if len(vec) != c.VECTOR_DIM:
        out.add("DIM_MISMATCH", path, f"{key} has {len(vec)} values, contract requires {c.VECTOR_DIM}")
        return
    for j, v in enumerate(vec):
        if not _is_num(v):
            out.add("WRONG_TYPE", f"{path}/{j}", f"{key}[{j}] must be a number, got {v!r}")
        elif not _finite(v):
            out.add("NON_FINITE_VALUE", f"{path}/{j}", f"{key}[{j}] is not finite")
        else:
            lo, hi = c.JOINT_LIMITS[j]
            if not lo <= v <= hi:
                out.add("OUT_OF_LIMITS", f"{path}/{j}", f"{c.JOINT_NAMES[j]}: {v} outside [{lo}, {hi}] {c.JOINT_UNITS[j]}")


def _check_timestamps(frames: list, ep_path: str, fps: Optional[int], tol: float, out: _Collector) -> None:
    ts = []
    for j, fr in enumerate(frames):
        t = fr.get("timestamp") if isinstance(fr, dict) else None
        p = f"{ep_path}/frames/{j}/timestamp"
        if not _is_num(t):
            out.add("MISSING_FIELD" if t is None else "WRONG_TYPE", p, f"timestamp must be a number (seconds), got {t!r}")
            return
        if not _finite(t):
            out.add("NON_FINITE_VALUE", p, "timestamp is not finite")
            return
        ts.append(float(t))
    broken = False
    for j in range(1, len(ts)):
        if not ts[j] > ts[j - 1]:
            broken = True
            out.add("TIMESTAMP_NOT_MONOTONIC", f"{ep_path}/frames/{j}/timestamp", f"{ts[j]} is not greater than previous {ts[j - 1]}")
    if broken or fps is None:
        return  # drift is only evaluated on strictly increasing timestamps and a valid fps
    for j, t in enumerate(ts):
        want = j / fps
        if abs(t - want) > tol:
            out.add(
                "TIMESTAMP_FPS_DRIFT",
                f"{ep_path}/frames/{j}/timestamp",
                f"{t} differs from frame_index/fps = {want:.6f} by {abs(t - want):.6f} s (tolerance {tol} s)",
            )


def _check_episodes(doc: dict, fps: Optional[int], tol: float, task_ids: set, out: _Collector) -> None:
    eps = doc.get("episodes")
    if not isinstance(eps, list) or not eps:
        out.add("NO_EPISODES", "/episodes", "episodes must be a non-empty list")
        return
    seen: set = set()
    next_index = 0
    expected_from = 0
    for i, ep in enumerate(eps):
        p = _ptr("episodes", i)
        if not isinstance(ep, dict):
            out.add("WRONG_TYPE", p, "episode must be an object")
            continue
        idx = ep.get("episode_index")
        if not _is_int(idx) or idx < 0:
            out.add("WRONG_TYPE" if "episode_index" in ep else "MISSING_FIELD", p + "/episode_index", f"episode_index must be an integer >= 0, got {idx!r}")
        elif idx in seen:
            out.add("EPISODE_INDEX_DUPLICATE", p + "/episode_index", f"episode_index {idx} already used by an earlier episode")
        else:
            seen.add(idx)
            if idx != next_index:
                out.add("EPISODE_INDEX_GAP", p + "/episode_index", f"expected episode_index {next_index}, got {idx}")
            next_index = idx + 1
        ti = ep.get("task_index")
        # type-check BEFORE the set lookup: lists/dicts are unhashable
        if not _is_int(ti):
            out.add("WRONG_TYPE" if "task_index" in ep else "TASK_MISSING", p + "/task_index", f"task_index must be an integer, got {ti!r}")
        elif task_ids and ti not in task_ids:
            out.add("TASK_MISSING", p + "/task_index", f"task_index {ti!r} is not defined in tasks")
        frames = ep.get("frames")
        if not isinstance(frames, list):
            out.add("WRONG_TYPE" if "frames" in ep else "MISSING_FIELD", p + "/frames", "frames must be a list")
            frames = []
            nframes = None
        else:
            nframes = len(frames)
        length = ep.get("length")
        if nframes == 0:
            out.add("EPISODE_EMPTY", p, "episode has no frames")
        elif not _is_int(length):
            out.add("WRONG_TYPE" if "length" in ep else "MISSING_FIELD", p + "/length", f"length must be an integer, got {length!r}")
        elif nframes is not None and length != nframes:
            # includes length == 0 with a non-empty frames list
            out.add("EPISODE_LENGTH_MISMATCH", p + "/length", f"length {length!r} but {nframes} frames")
        # boundaries
        frm, to = ep.get("dataset_from_index"), ep.get("dataset_to_index")
        if not _is_int(frm) or not _is_int(to):
            out.add("MISSING_FIELD", p + "/dataset_from_index", "dataset_from_index and dataset_to_index must be integers")
        else:
            if frm != expected_from:
                out.add("EPISODE_BOUNDARY_GAP", p + "/dataset_from_index", f"starts at {frm}, previous episode ended at {expected_from}")
            if nframes is not None and to - frm != nframes:
                out.add("EPISODE_BOUNDARY_GAP", p + "/dataset_to_index", f"to-from = {to - frm} but {nframes} frames")
            expected_from = frm + (nframes if nframes is not None else 0)
        # frames
        for j, fr in enumerate(frames):
            fp = f"{p}/frames/{j}"
            if not isinstance(fr, dict):
                out.add("WRONG_TYPE", fp, "frame must be an object")
                continue
            if fr.get("frame_index") != j:
                out.add("FRAME_INDEX_MISMATCH", fp + "/frame_index", f"expected {j}, got {fr.get('frame_index')!r}")
            for key in c.VECTOR_FEATURES:
                _check_vector(fr, key, fp, out)
        if frames:
            _check_timestamps(frames, p, fps, tol, out)


def _validate(doc: Any, out: _Collector) -> None:
    if not isinstance(doc, dict):
        out.add("MALFORMED_DOCUMENT", "", f"top-level value must be an object, got {type(doc).__name__}")
        return
    ver = doc.get("schema_version")
    if ver is None:
        out.add("MISSING_FIELD", "/schema_version", "schema_version is required")
        return
    if not isinstance(ver, str):
        out.add("WRONG_TYPE", "/schema_version", f"schema_version must be a string, got {ver!r}")
        return
    if ver != c.SCHEMA_VERSION:
        out.add("SCHEMA_VERSION_UNKNOWN", "/schema_version", f"unsupported schema_version {ver!r}; this validator supports {c.SCHEMA_VERSION!r}")
        return  # unknown version: do not guess the rest of the layout
    if doc.get("synthetic") is not True:
        out.add("NOT_SYNTHETIC", "/synthetic", "synthetic must be exactly true; real robot/person data is out of scope")
    _check_license(doc, out)
    if not isinstance(doc.get("dataset_name"), str) or not doc.get("dataset_name", "").strip():
        out.add("MISSING_FIELD", "/dataset_name", "dataset_name must be a non-empty string")
    fps = _check_fps(doc, out)
    tol = _check_tolerance(doc, fps, out)
    task_ids = _check_tasks(doc, out)
    _check_features(doc, fps, out)
    _check_episodes(doc, fps, tol, task_ids, out)


# --------------------------------------------------------------------------- public API


def validate_document(doc: Any) -> tuple[list[Diagnostic], bool]:
    """Return ``(diagnostics, truncated)``. Never raises."""
    out = _Collector()
    try:
        _validate(doc, out)
    except Exception as exc:  # fail closed
        out.items.append(Diagnostic("INTERNAL_ERROR", "", f"unexpected {type(exc).__name__}", c.CODES["INTERNAL_ERROR"][1]))
    return out.items, out.truncated


class _NonFiniteLiteral(ValueError):
    """Raised by the JSON parser for NaN / Infinity / -Infinity literals."""


def _reject_constant(name: str) -> None:
    raise _NonFiniteLiteral(name)


def validate_text(text: str) -> tuple[list[Diagnostic], bool]:
    """Parse strict JSON text and validate it. Never raises."""
    if len(text.encode("utf-8", "replace")) > c.MAX_FILE_BYTES:
        return [Diagnostic("FILE_TOO_LARGE", "", f"more than {c.MAX_FILE_BYTES} bytes", c.CODES["FILE_TOO_LARGE"][1])], False
    try:
        doc = json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        return [Diagnostic("MALFORMED_JSON", "", f"line {exc.lineno} column {exc.colno}: {exc.msg}", c.CODES["MALFORMED_JSON"][1])], False
    except _NonFiniteLiteral as exc:  # NaN / Infinity / -Infinity literals
        return [Diagnostic("NON_FINITE_VALUE", "", f"JSON literal {exc} is not allowed", c.CODES["NON_FINITE_VALUE"][1])], False
    except ValueError as exc:  # e.g. integer literal with too many digits
        return [Diagnostic("MALFORMED_JSON", "", f"unparseable value: {exc}", c.CODES["MALFORMED_JSON"][1])], False
    except RecursionError:
        return [Diagnostic("MALFORMED_JSON", "", "nesting too deep", c.CODES["MALFORMED_JSON"][1])], False
    return validate_document(doc)


def validate_file(path: str) -> tuple[list[Diagnostic], bool]:
    """Read and validate one file. Unreadable files yield ``FILE_UNREADABLE``."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(c.MAX_FILE_BYTES + 1)
    except OSError as exc:
        return [Diagnostic("FILE_UNREADABLE", "", f"{type(exc).__name__}: {exc.strerror or exc}", c.CODES["FILE_UNREADABLE"][1])], False
    if len(raw) > c.MAX_FILE_BYTES:
        return [Diagnostic("FILE_TOO_LARGE", "", f"more than {c.MAX_FILE_BYTES} bytes", c.CODES["FILE_TOO_LARGE"][1])], False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [Diagnostic("MALFORMED_JSON", "", f"not UTF-8: {exc.reason}", c.CODES["MALFORMED_JSON"][1])], False
    return validate_text(text)


# --------------------------------------------------------------------------- CLI


def build_report(results: list[tuple[str, list[Diagnostic], bool]]) -> dict:
    files = [
        {
            "file": name,
            "ok": not diags,
            "diagnostic_count": len(diags),
            "truncated": trunc,
            "diagnostics": [d.as_dict() for d in diags],
        }
        for name, diags, trunc in results
    ]
    return {
        "report_version": c.REPORT_VERSION,
        "schema_version": c.SCHEMA_VERSION,
        "ok": all(f["ok"] for f in files),
        "files": files,
    }


def format_text(report: dict) -> str:
    lines = []
    for f in report["files"]:
        lines.append(f"{'OK  ' if f['ok'] else 'FAIL'} {f['file']}")
        for d in f["diagnostics"]:
            where = d["path"] or "(document)"
            lines.append(f"  [{d['code']}] {where}: {d['message']}")
            lines.append(f"      hint: {d['hint']}")
        if f["truncated"]:
            lines.append(f"  ... output truncated at {c.MAX_DIAGNOSTICS} diagnostics")
    bad = sum(1 for f in report["files"] if not f["ok"])
    lines.append(f"{len(report['files']) - bad} valid, {bad} invalid ({c.SCHEMA_VERSION})")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="dq_validate.py",
        description="Validate SYNTHETIC episode metadata (contract synthetic-episodes-meta/v1). Offline, stdlib only.",
        epilog="Exit codes: 0 all valid, 1 at least one invalid, 2 usage or I/O error.",
    )
    ap.add_argument("files", nargs="*", help="JSON metadata file(s) to validate")
    ap.add_argument("--format", choices=("text", "json"), default="text", help="output format (default: text)")
    ap.add_argument("--list-codes", action="store_true", help="print every diagnostic code with its meaning and exit")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 2
    if args.list_codes:
        for code, (meaning, hint) in c.CODES.items():
            print(f"{code}\n    {meaning}\n    hint: {hint}")
        return 0
    if not args.files:
        ap.print_usage(sys.stderr)
        print("error: give at least one file (or --list-codes)", file=sys.stderr)
        return 2
    results = [(f, *validate_file(f)) for f in args.files]
    report = build_report(results)
    print(json.dumps(report, indent=2) if args.format == "json" else format_text(report))
    if any(d.code == "FILE_UNREADABLE" for _, diags, _ in results for d in diags):
        return 2
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
