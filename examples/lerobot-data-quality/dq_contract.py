"""Constants of the synthetic-episode metadata contract v1 (stdlib only).

SYNTHETIC, offline, non-actuating. This module is data only: it imports no
LeRobot, torch, Hugging Face or ROS code. The layout of the six-joint arm
(names, units, limits) and the two camera keys mirror the simulated
``ros2-obs-action/v1`` contract in ``examples/cloud-robotics/mock-policy/``
(a test checks that they stay in sync whenever that directory is present).

The field names used here are *this contract's own* names. They are modelled
on common dataset-metadata ideas, but they are NOT asserted to be identical
to the on-disk layout of any particular LeRobotDataset release; see the
"Documented, not run" section of the README.
"""

from __future__ import annotations

SCHEMA_VERSION = "synthetic-episodes-meta/v1"
REPORT_VERSION = "dq-report/v1"

# (name, unit, lower limit, upper limit) -- same order as the mock-policy contract.
JOINTS = (
    ("shoulder_pan", "rad", -3.1416, 3.1416),
    ("shoulder_lift", "rad", -1.7, 1.7),
    ("elbow_flex", "rad", -1.7, 1.7),
    ("wrist_flex", "rad", -1.8, 1.8),
    ("wrist_roll", "rad", -3.1416, 3.1416),
    ("gripper", "m", 0.0, 0.08),
)
JOINT_NAMES = tuple(j[0] for j in JOINTS)
JOINT_UNITS = tuple(j[1] for j in JOINTS)
JOINT_LIMITS = tuple((j[2], j[3]) for j in JOINTS)
VECTOR_DIM = len(JOINTS)

STATE_KEY = "observation.state"
ACTION_KEY = "action"
VECTOR_FEATURES = (STATE_KEY, ACTION_KEY)
VECTOR_DTYPE = "float32"

# Required camera feature keys (same keys as the mock-policy camera mapping).
CAMERA_PREFIX = "observation.images."
REQUIRED_CAMERA_KEYS = ("observation.images.front", "observation.images.wrist")
CAMERA_DTYPES = ("video", "image")
CAMERA_SHAPE_NAMES = ["height", "width", "channels"]
CAMERA_ENCODINGS = {"rgb8": 3, "mono8": 1}  # encoding -> channels
CAMERA_REQUIRED_FIELDS = ("width", "height", "encoding", "fps")
MAX_CAMERA_DIM = 1024

# Licences accepted for SYNTHETIC data in this repository (SPDX identifiers).
ALLOWED_LICENSES = (
    "CC0-1.0",
    "Apache-2.0",
    "MIT",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "BSD-3-Clause",
)

MAX_FPS = 1000
DEFAULT_TIMESTAMP_TOLERANCE_S = 0.001
MAX_FILE_BYTES = 1024 * 1024
MAX_DIAGNOSTICS = 100

# code -> (what it means, how to fix it). Stable strings, safe to log.
CODES = {
    "MALFORMED_JSON": ("The file is not valid UTF-8 JSON.", "Fix the syntax error at the reported line/column."),
    "FILE_TOO_LARGE": ("The file exceeds the size bound.", "Synthetic fixtures must stay tiny (<= 1 MiB)."),
    "FILE_UNREADABLE": ("The file could not be read.", "Check the path and permissions."),
    "NON_FINITE_VALUE": ("NaN or Infinity found.", "Use finite numbers only; strict JSON has no NaN/Infinity."),
    "MALFORMED_DOCUMENT": ("The top-level value is not a JSON object.", "Wrap the metadata in one JSON object."),
    "MISSING_FIELD": ("A required field is absent.", "Add the field named in the path."),
    "WRONG_TYPE": ("A field has the wrong JSON type.", "Use the type given in the schema."),
    "SCHEMA_VERSION_UNKNOWN": (
        "schema_version is not supported by this validator.",
        "Use 'synthetic-episodes-meta/v1' or upgrade the validator; nothing else is checked.",
    ),
    "NOT_SYNTHETIC": ("'synthetic' is not true.", "This contract only accepts 100% synthetic data; set synthetic=true only if it is."),
    "LICENSE_MISSING": ("The license field is absent or empty.", "Add an SPDX id, e.g. 'CC0-1.0'."),
    "LICENSE_NOT_ALLOWED": ("The license is not on the allow-list.", "Use one of the allowed SPDX ids (see --list-codes / README)."),
    "FPS_INVALID": ("fps is missing or not an integer in 1..1000.", "Set a positive integer frame rate."),
    "TOLERANCE_INVALID": ("timestamp_tolerance_s is not usable.", "Use a number > 0 and < 0.5/fps, or omit it for the default."),
    "FEATURE_MISSING": ("A required feature is absent.", "Declare observation.state and action under 'features'."),
    "FEATURE_DTYPE_BAD": ("A feature has an unsupported dtype.", "Vectors use 'float32'; cameras use 'video' or 'image'."),
    "FEATURE_SHAPE_BAD": ("A feature shape is malformed.", "Vectors: [6]. Cameras: [height, width, channels]."),
    "FEATURE_NAMES_MISMATCH": ("Feature names differ from the contract.", "Use the fixed joint order from the contract table."),
    "DIM_MISMATCH": ("A vector length disagrees with the contract dimension (6).", "Make shape, names, units and every frame vector length 6."),
    "UNIT_MISMATCH": ("A declared unit differs from the contract.", "Use the unit from the contract table (rad for joints, m for gripper)."),
    "OUT_OF_LIMITS": ("A value is outside the joint limits.", "Keep values inside the per-joint limits of the contract."),
    "CAMERA_METADATA_MISSING": ("A required camera or its metadata is absent.", "Declare the camera feature with a 'camera' block (width, height, encoding, fps)."),
    "CAMERA_METADATA_INVALID": ("Camera metadata is inconsistent or out of range.", "Make width/height/encoding/fps agree with the feature shape and dataset fps."),
    "TASK_MISSING": ("A task description is missing or unresolvable.", "Provide non-empty tasks[] and a valid task_index per episode."),
    "NO_EPISODES": ("The episodes list is missing or empty.", "A dataset needs at least one episode."),
    "EPISODE_EMPTY": ("An episode has no frames.", "Remove it or add frames; zero-length episodes are rejected."),
    "EPISODE_INDEX_DUPLICATE": ("Two episodes share an episode_index.", "Give every episode a unique, increasing index."),
    "EPISODE_INDEX_GAP": ("episode_index values are not 0..N-1 in order.", "Renumber episodes contiguously from 0."),
    "EPISODE_LENGTH_MISMATCH": ("'length' differs from the number of frames.", "Set length to len(frames)."),
    "EPISODE_BOUNDARY_GAP": ("Episode boundaries are not contiguous.", "dataset_from_index must equal the previous dataset_to_index (first: 0) and to-from must equal the frame count."),
    "FRAME_INDEX_MISMATCH": ("frame_index is not the frame's position.", "Number frames 0..length-1 within each episode."),
    "TIMESTAMP_NOT_MONOTONIC": ("Timestamps are not strictly increasing.", "Sort/regenerate timestamps; equal values are also rejected."),
    "TIMESTAMP_FPS_DRIFT": ("A timestamp is inconsistent with fps beyond the tolerance.", "Expected frame_index/fps within timestamp_tolerance_s."),
    "INTERNAL_ERROR": ("The validator hit an unexpected error.", "Report this; the document is treated as invalid (fail closed)."),
}
