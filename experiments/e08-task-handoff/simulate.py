#!/usr/bin/env python3
"""E08: deterministic *single-process* fictional robot-task handoff.

Never use this toy as a real ROS action gateway, authorization service, or
Kubernetes migration implementation. It has no durable/independent authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "inspection-v0.1.json"
VERSION = "e08-synthetic-mission-v0.1"
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class Rejected(ValueError):
    """Invalid fixture, checkpoint, transfer, or simulated command."""


def reject_if(condition: bool, reason: str) -> None:
    if condition:
        raise Rejected(reason)


def exact_keys(item: Any, expected: set[str], where: str) -> dict[str, Any]:
    reject_if(not isinstance(item, dict) or set(item) != expected, f"{where}: fields")
    return item


def valid_id(value: Any, where: str) -> None:
    reject_if(not isinstance(value, str) or ID.fullmatch(value) is None, f"{where}: identifier")


def valid_names(value: Any, where: str) -> list[str]:
    reject_if(not isinstance(value, list) or not value, f"{where}: nonempty list")
    for name in value:
        valid_id(name, where)
    reject_if(len(set(value)) != len(value), f"{where}: duplicate")
    return value


def integer(value: Any, where: str, minimum: int = 0) -> None:
    reject_if(type(value) is not int or value < minimum, f"{where}: nonnegative integer")


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def validate_fixture(data: Any) -> dict[str, Any]:
    root = exact_keys(data, {"schema_version", "mission", "robot", "checkpoint", "observation", "destination", "handoff_tick"}, "root")
    reject_if(root["schema_version"] != VERSION, "schema: unsupported version")
    mission = exact_keys(root["mission"], {"task_id", "waypoints"}, "mission")
    valid_id(mission["task_id"], "task_id")
    waypoints = valid_names(mission["waypoints"], "waypoints")
    robot = exact_keys(root["robot"], {"robot_id", "frame_id", "map_revision", "capabilities"}, "robot")
    dest = exact_keys(root["destination"], {"execution_id", "robot_id", "frame_id", "map_revision", "capabilities"}, "destination")
    for key in ("robot_id", "frame_id", "map_revision"):
        valid_id(robot[key], f"robot.{key}")
        valid_id(dest[key], f"destination.{key}")
        reject_if(robot[key] != dest[key], f"destination: incompatible {key}")
    capabilities = valid_names(robot["capabilities"], "robot.capabilities")
    dest_caps = valid_names(dest["capabilities"], "destination.capabilities")
    reject_if("inspect_waypoint" not in capabilities or "inspect_waypoint" not in dest_caps,
              "destination: missing inspect_waypoint capability")
    reject_if(not set(dest_caps).issubset(set(capabilities)), "destination: unrecognized capability")
    checkpoint = exact_keys(root["checkpoint"], {"execution_id", "epoch", "cursor", "completed"}, "checkpoint")
    valid_id(checkpoint["execution_id"], "checkpoint.execution_id")
    valid_id(dest["execution_id"], "destination.execution_id")
    reject_if(checkpoint["execution_id"] == dest["execution_id"], "destination: same execution")
    integer(checkpoint["epoch"], "checkpoint.epoch", 1)
    integer(checkpoint["cursor"], "checkpoint.cursor")
    reject_if(checkpoint["cursor"] >= len(waypoints), "checkpoint: no remaining mission work")
    reject_if(not isinstance(checkpoint["completed"], list) or
              checkpoint["completed"] != waypoints[:checkpoint["cursor"]],
              "checkpoint: completed is not exact waypoint prefix")
    obs = exact_keys(root["observation"], {"captured_tick", "ttl_ticks"}, "observation")
    integer(obs["captured_tick"], "observation.captured_tick")
    integer(obs["ttl_ticks"], "observation.ttl_ticks", 1)
    integer(root["handoff_tick"], "handoff_tick")
    reject_if(not obs["captured_tick"] <= root["handoff_tick"] <=
              obs["captured_tick"] + obs["ttl_ticks"], "handoff: observation expired or future")
    return root


class ToyMission:
    """In-memory illustrative coordinator and simulated effect sink (not a trust boundary)."""

    def __init__(self, fixture: dict[str, Any]):
        self.config = validate_fixture(fixture)
        self.owner = fixture["checkpoint"]["execution_id"]
        self.epoch = fixture["checkpoint"]["epoch"]
        self.completed = list(fixture["checkpoint"]["completed"])
        self.accepted_effect_ids: set[str] = set()
        self.events: list[dict[str, Any]] = []

    def checkpoint(self) -> dict[str, Any]:
        state = {"task_id": self.config["mission"]["task_id"],
                 "execution_id": self.owner, "epoch": self.epoch,
                 "cursor": len(self.completed), "completed": list(self.completed)}
        return {"state": state, "sha256": sha256_json(state)}

    def transfer(self, bundle: Any, tick: int) -> None:
        exact_keys(bundle, {"state", "sha256"}, "bundle")
        reject_if(not isinstance(bundle["sha256"], str) or
                  bundle["sha256"] != sha256_json(bundle["state"]), "bundle: digest mismatch")
        reject_if(bundle["state"] != self.checkpoint()["state"], "bundle: stale state")
        obs = self.config["observation"]
        reject_if(type(tick) is not int or not obs["captured_tick"] <= tick <=
                  obs["captured_tick"] + obs["ttl_ticks"], "transfer: stale observation")
        old = self.owner
        self.owner = self.config["destination"]["execution_id"]
        self.epoch += 1
        self.events.append({"type": "simulated_transfer", "from": old,
                            "to": self.owner, "epoch": self.epoch, "tick": tick})

    def effect(self, *, executor: str, epoch: int, effect_id: str,
               waypoint: str, tick: int) -> str:
        """Return a typed verdict; never performs real robotic actuation."""
        valid_id(executor, "effect.executor")
        valid_id(effect_id, "effect.id")
        valid_id(waypoint, "effect.waypoint")
        integer(epoch, "effect.epoch", 1)
        integer(tick, "effect.tick")
        observation = self.config["observation"]
        if executor != self.owner or epoch != self.epoch:
            return "stale_or_unauthorized"
        if not observation["captured_tick"] <= tick <= observation["captured_tick"] + observation["ttl_ticks"]:
            return "stale_observation"
        if effect_id in self.accepted_effect_ids:
            return "duplicate_effect"
        remaining = self.config["mission"]["waypoints"][len(self.completed):]
        if not remaining or remaining[0] != waypoint:
            return "wrong_next_waypoint"
        self.completed.append(waypoint)
        self.accepted_effect_ids.add(effect_id)
        self.events.append({"type": "simulated_effect_accepted", "executor": executor,
                            "epoch": epoch, "effect_id": effect_id, "waypoint": waypoint, "tick": tick})
        return "accepted"


def run_demo(fixture: dict[str, Any]) -> dict[str, Any]:
    """Exercise one illustrative branch; other fault schedules remain future work."""
    validated = validate_fixture(fixture)
    toy = ToyMission(validated)
    snapshot = toy.checkpoint()
    start = validated["handoff_tick"]
    toy.transfer(snapshot, tick=start)
    cursor = validated["checkpoint"]["cursor"]
    destinations = validated["mission"]["waypoints"][cursor:]
    for i, waypoint in enumerate(destinations):
        outcome = toy.effect(executor=toy.owner, epoch=toy.epoch,
                             effect_id=f"effect-{waypoint}", waypoint=waypoint, tick=start+i)
        reject_if(outcome != "accepted", f"demo: unable to complete {waypoint}: {outcome}")
    stale = toy.effect(executor=validated["checkpoint"]["execution_id"],
                       epoch=validated["checkpoint"]["epoch"],
                       effect_id="old-worker-attempt", waypoint=destinations[-1], tick=start)
    duplicate = toy.effect(executor=toy.owner, epoch=toy.epoch,
                           effect_id=f"effect-{destinations[0]}", waypoint=destinations[0], tick=start)
    expired_tick = validated["observation"]["captured_tick"] + validated["observation"]["ttl_ticks"] + 1
    expired = toy.effect(executor=toy.owner, epoch=toy.epoch,
                         effect_id="late-attempt", waypoint=destinations[0], tick=expired_tick)
    return {
        "status": "synthetic_single_process_only",
        "fixture_sha256": sha256_json(validated),
        "task_id": validated["mission"]["task_id"],
        "final_execution": toy.owner,
        "final_epoch": toy.epoch,
        "completed_waypoints": toy.completed,
        "rejection_checks": {"stale_origin": stale, "replay": duplicate, "expired": expired},
        "events": toy.events,
        "limitations": "Not ROS 2, Kubernetes, distributed migration, durable fencing, or real robot safety"
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE, help="Synthetic JSON fixture")
    parser.add_argument("--validate-only", action="store_true", help="Check contract without simulation")
    args = parser.parse_args(argv)
    try:
        fixture = validate_fixture(json.loads(args.fixture.read_text(encoding="utf-8")))
        result = ({"status": "fixture_valid", "fixture_sha256": sha256_json(fixture)}
                  if args.validate_only else run_demo(fixture))
    except (OSError, json.JSONDecodeError, Rejected) as exc:
        print(f"E08 rejected: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
