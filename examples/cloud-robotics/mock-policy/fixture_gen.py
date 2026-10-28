"""Bounded, deterministic generator for the synthetic fixtures. Stdlib only.

All data is synthetic: random bytes from a fixed seed and joint values inside
the contract limits. No real images, robots, addresses or private data.

    python3 fixture_gen.py --check   # compare with committed fixtures (exit 1 on drift)
    python3 fixture_gen.py --write   # regenerate fixtures/ (review the diff!)
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import sys
from pathlib import Path

import contract as c
import mock_policy

HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE / "fixtures"
SEED = 42
MAX_FIXTURES = 8  # hard bound on generated sequences
START_NS = 1_000_000_000
PERIOD_NS = 100_000_000  # 10 Hz simulated source clock
IMAGE_W, IMAGE_H = 2, 2  # tiny on purpose


def build_observation(sequence_id: int, seed: int = SEED) -> dict:
    if not 1 <= sequence_id <= MAX_FIXTURES:
        raise ValueError(f"sequence_id must be in 1..{MAX_FIXTURES}")
    rng = random.Random(f"{seed}:obs:{sequence_id}")
    cameras = []
    for name, key in c.CAMERA_KEYS.items():
        raw = bytes(rng.randrange(256) for _ in range(IMAGE_W * IMAGE_H * 3))
        cameras.append(
            {
                "name": name,
                "key": key,
                "width": IMAGE_W,
                "height": IMAGE_H,
                "encoding": "rgb8",
                "data_b64": base64.b64encode(raw).decode("ascii"),
            }
        )
    values = [round(rng.uniform(0.25 * lo + 0.25 * hi, 0.75 * hi + 0.25 * lo), 6) for lo, hi in c.JOINT_LIMITS]
    return {
        "contract_version": c.CONTRACT_VERSION,
        "simulated": True,
        "observation_id": f"obs-{sequence_id:04d}",
        "sequence_id": sequence_id,
        "source_timestamp_ns": START_NS + sequence_id * PERIOD_NS,
        "frame_name": "base_link",
        "task_id": "task-synthetic-reach",
        "ttl_ms": 500,
        "cameras": cameras,
        "state": {"names": list(c.JOINT_NAMES), "units": list(c.JOINT_UNITS), "values": values},
    }


def build_all(count: int = 2) -> dict:
    """Return {filename: dict} for ``count`` observation/action pairs."""
    if not 1 <= count <= MAX_FIXTURES:
        raise ValueError(f"count must be in 1..{MAX_FIXTURES}")
    policy = mock_policy.MockPolicy(seed=SEED)
    files = {}
    for seq in range(1, count + 1):
        obs = build_observation(seq)
        files[f"observation_{seq:04d}.json"] = obs
        files[f"action_{seq:04d}.json"] = policy.act(obs)
    return files


def render(doc: dict) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    drift = False
    for name, doc in build_all().items():
        path = FIXTURE_DIR / name
        text = render(doc)
        if args.write:
            FIXTURE_DIR.mkdir(exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(HERE)}")
        elif not path.exists() or path.read_text(encoding="utf-8") != text:
            print(f"DRIFT {path.relative_to(HERE)}", file=sys.stderr)
            drift = True
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
