"""Constants of contract v1 (simulated educational contract; stdlib only).

This module is data only. It must not import any policy, model or ROS code.
The JSON Schema files in ``schema/`` describe the same contract; a unit test
checks that the key lists below and the schemas stay in sync.
"""

from __future__ import annotations

CONTRACT_VERSION = "ros2-obs-action/v1"

# One fixed, ordered joint layout: (name, unit, lower limit, upper limit).
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
ACTION_DIM = len(JOINTS)

# Camera name (ROS-side name) -> key used in the observation dictionary.
CAMERA_KEYS = {
    "front_rgb": "observation.images.front",
    "wrist_rgb": "observation.images.wrist",
}
REQUIRED_CAMERAS = tuple(CAMERA_KEYS)
CAMERA_ENCODINGS = {"rgb8": 3, "mono8": 1}  # encoding -> bytes per pixel

ACTION_SPACE = "joint_position_target"
# Allow-list: anything else (cmd_vel, shell, raw motor ...) is rejected.
ALLOWED_COMMANDS = ("set_joint_targets",)

# Bounds (kept small so a hostile message cannot cause large work).
MAX_TIMESTAMP_NS = 2**53  # exact in JSON / float64
MAX_SEQUENCE_ID = 2**53
MAX_TTL_MS = 10_000
MAX_CAMERA_DIM = 1024
MAX_CAMERA_BYTES = 1024 * 1024

OBSERVATION_FIELDS = (
    "contract_version",
    "simulated",
    "observation_id",
    "sequence_id",
    "source_timestamp_ns",
    "frame_name",
    "task_id",
    "ttl_ms",
    "cameras",
    "state",
)
CAMERA_FIELDS = ("name", "key", "width", "height", "encoding", "data_b64")
STATE_FIELDS = ("names", "units", "values")
ACTION_FIELDS = (
    "contract_version",
    "simulated",
    "source_id",
    "sequence_id",
    "observation_id",
    "created_timestamp_ns",
    "ttl_ms",
    "task_id",
    "model_id",
    "model_revision",
    "command",
    "action_space",
    "units",
    "values",
)
