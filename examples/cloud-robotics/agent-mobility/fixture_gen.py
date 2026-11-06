#!/usr/bin/env python3
"""Deterministically (re)generate the SYNTHETIC fixtures under ``fixtures/``.

    python3 fixture_gen.py            # rewrite the fixture files
    python3 fixture_gen.py --check    # exit 1 if committed fixtures differ from the generator

Every fixture is fictional: made-up identifiers, logical ticks, no real robot, map or data.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

import mission_state as ms
from mission_state import Reason as R

HERE = Path(__file__).resolve().parent
BUNDLE_DIR = HERE / "fixtures" / "bundles"
SCRIPT_DIR = HERE / "fixtures" / "scripts"

TASK = "inspection-001"
STEPS = ["wp-01", "wp-02", "wp-03", "wp-04", "wp-05"]
REQUIREMENTS = {
    "robot_class": "sim-mobile-base", "frame_id": "map", "map_revision": "synthetic-map-v1",
    "units": {"length": "m", "angle": "rad", "time": "s"},
    "capabilities": ["inspect_waypoint", "report_status"],
    "sensors": [{"name": "front_range", "type": "range", "units": "m"},
                {"name": "camera_front", "type": "rgb_image", "units": "pixel"}],
    "action": {"command": "navigate_to_waypoint", "space": "waypoint_goal", "units": "m"},
}


def profile(executor_id: str, **overrides: Any) -> dict[str, Any]:
    base = {
        "executor_id": executor_id, "supported_schemas": [ms.SCHEMA],
        "robot_class": "sim-mobile-base", "frame_id": "map", "map_revision": "synthetic-map-v1",
        "units": {"length": "m", "angle": "rad", "time": "s"},
        "capabilities": ["inspect_waypoint", "report_status", "extra_skill"],
        "sensors": [{"name": "front_range", "type": "range", "units": "m"},
                    {"name": "camera_front", "type": "rgb_image", "units": "pixel"}],
        "actions": [{"command": "navigate_to_waypoint", "space": "waypoint_goal", "units": "m"}],
    }
    base.update(copy.deepcopy(overrides))
    return base


def ledger_ids(n: int) -> list[str]:
    return [f"{TASK}-cloud-01-e1-s{i}" for i in range(n)]


def base_bundle(cursor: int = 2) -> dict[str, Any]:
    return ms.seal({
        "schema": ms.SCHEMA, "simulated": True,
        "mission": {"task_id": TASK, "mission_revision": 1, "steps": list(STEPS)},
        "progress": {"cursor": cursor, "completed": STEPS[:cursor], "committed_effect_ids": ledger_ids(cursor)},
        "ownership": {"state_owner": "cloud-01", "epoch": 1, "lease_expires_tick": 50},
        "handoff": {"handoff_id": f"{TASK}-h001", "nonce": f"nonce-{TASK}-0001", "sequence": 1,
                    "from_executor": "cloud-01", "to_executor": "edge-01", "issued_tick": 4, "expires_tick": 14},
        "requirements": copy.deepcopy(REQUIREMENTS),
        "rollback": {"on_failure": "reissue_to_origin", "origin_executor": "cloud-01", "resume_from": "effect_ledger"},
    })


def base_context(cursor: int = 2) -> dict[str, Any]:
    return {"now_tick": 5,
            "coordinator": {"owner": "cloud-01", "epoch": 1, "last_sequence": 0, "seen_nonces": [],
                            "ledger_effect_ids": ledger_ids(cursor)},
            "destination_profile": profile("edge-01")}


def _edit(bundle_fn: Callable[[dict], None] | None = None, ctx_fn: Callable[[dict], None] | None = None,
          reseal: bool = True) -> Callable[[], tuple[Any, dict]]:
    def build() -> tuple[Any, dict]:
        bundle, ctx = base_bundle(), base_context()
        if bundle_fn:
            bundle_fn(bundle)
            if reseal:
                bundle = ms.seal(bundle)
        if ctx_fn:
            ctx_fn(ctx)
        return bundle, ctx
    return build


def _set(path: str, value: Any) -> Callable[[dict], None]:
    def fn(doc: dict) -> None:
        *parents, last = path.split(".")
        for p in parents:
            doc = doc[p]
        doc[last] = value
    return fn


def _del(path: str) -> Callable[[dict], None]:
    def fn(doc: dict) -> None:
        *parents, last = path.split(".")
        for p in parents:
            doc = doc[p]
        del doc[last]
    return fn


def _dest(**overrides: Any) -> Callable[[dict], None]:
    return lambda ctx: ctx["destination_profile"].update(copy.deepcopy(overrides))


def _both(*fns: Callable[[dict], None]) -> Callable[[dict], None]:
    def fn(doc: dict) -> None:
        for f in fns:
            f(doc)
    return fn


def _complete(bundle: dict) -> None:
    bundle["progress"] = {"cursor": 5, "completed": list(STEPS), "committed_effect_ids": ledger_ids(5)}


def _complete_ctx(ctx: dict) -> None:
    ctx["coordinator"]["ledger_effect_ids"] = ledger_ids(5)


def bundle_cases() -> dict[str, tuple[str, str | None, Callable[[], tuple[Any, dict]]]]:
    sensors = REQUIREMENTS["sensors"]
    return {
        "valid-handoff": ("Control: a well-formed, compatible, fresh handoff is accepted.", None, _edit()),
        # shape
        "malformed-document": ("Bundle is a JSON array, not an object.", R.MALFORMED_DOCUMENT,
                               lambda: ([], base_context())),
        "missing-field": ("The rollback block is absent.", R.MISSING_FIELD, _edit(_del("rollback"))),
        "unknown-field": ("An undeclared top-level field is present.", R.UNKNOWN_FIELD, _edit(_set("extra", 1))),
        "wrong-type": ("ownership.epoch is a string.", R.WRONG_TYPE, _edit(_set("ownership.epoch", "1"))),
        "bad-value": ("handoff.sequence is 0 (must be >= 1).", R.BAD_VALUE, _edit(_set("handoff.sequence", 0))),
        "bad-identifier": ("mission.task_id contains characters outside the identifier alphabet.",
                           R.BAD_IDENTIFIER, _edit(_set("mission.task_id", "bad id!"))),
        "unsupported-schema-version": ("schema names a version this validator does not implement.",
                                       R.UNSUPPORTED_SCHEMA_VERSION, _edit(_set("schema", "mission-state/v2"))),
        "not-simulated": ("simulated is false; v1 documents are simulation-only.", R.NOT_SIMULATED,
                          _edit(_set("simulated", False))),
        "digest-mismatch": ("Content changed after sealing (digest not recomputed).", R.DIGEST_MISMATCH,
                            _edit(_set("mission.mission_revision", 2), reseal=False)),
        "progress-inconsistent": ("completed is not the step prefix of length cursor.", R.PROGRESS_INCONSISTENT,
                                  _edit(_set("progress.completed", ["wp-02", "wp-01"]))),
        "inconsistent-bundle": ("ownership.state_owner disagrees with handoff.from_executor.",
                                R.INCONSISTENT_BUNDLE, _edit(_set("ownership.state_owner", "other-01"))),
        # freshness
        "bundle-expired": ("Validated after handoff.expires_tick.", R.BUNDLE_EXPIRED,
                           _edit(ctx_fn=_set("now_tick", 20))),
        "bundle-from-future": ("Validated before handoff.issued_tick (clock disagreement).", R.BUNDLE_FROM_FUTURE,
                               _edit(ctx_fn=_set("now_tick", 2))),
        # parties, ownership, replay
        "same-executor": ("Source and destination are the same executor.", R.SAME_EXECUTOR,
                          _edit(_set("handoff.to_executor", "cloud-01"))),
        "wrong-destination": ("Bundle is addressed to an executor other than the validating one.",
                              R.WRONG_DESTINATION, _edit(_set("handoff.to_executor", "edge-02"))),
        "replayed-nonce": ("Nonce was already consumed by an earlier commit.", R.REPLAYED_NONCE,
                           _edit(ctx_fn=_set("coordinator.seen_nonces", [f"nonce-{TASK}-0001"]))),
        "stale-sequence": ("Fresh nonce but sequence is not above the last accepted one.", R.STALE_SEQUENCE,
                           _edit(ctx_fn=_set("coordinator.last_sequence", 1))),
        "stale-epoch": ("Bundle was sealed under epoch 1 but ownership has since advanced to epoch 2.",
                        R.STALE_EPOCH, _edit(ctx_fn=_set("coordinator.epoch", 2))),
        "wrong-state-owner": ("Coordinator says someone else owns the mission state.", R.WRONG_STATE_OWNER,
                              _edit(ctx_fn=_set("coordinator.owner", "other-01"))),
        "stale-checkpoint": ("Bundle progress is behind the authoritative effect ledger.", R.STALE_CHECKPOINT,
                             _edit(ctx_fn=_set("coordinator.ledger_effect_ids", ledger_ids(3)))),
        "mission-complete": ("Every step is already committed; there is nothing to hand off.",
                             R.MISSION_COMPLETE, _edit(_complete, _complete_ctx)),
        # compatibility
        "schema-not-supported": ("Destination supports only a different schema version.", R.SCHEMA_NOT_SUPPORTED,
                                 _edit(ctx_fn=_dest(supported_schemas=["mission-state/v2"]))),
        "robot-class-mismatch": ("Destination is a different robot class.", R.ROBOT_CLASS_MISMATCH,
                                 _edit(ctx_fn=_dest(robot_class="sim-arm"))),
        "frame-mismatch": ("Destination uses a different coordinate frame.", R.FRAME_MISMATCH,
                           _edit(ctx_fn=_dest(frame_id="odom"))),
        "map-revision-mismatch": ("Destination holds a different map revision.", R.MAP_REVISION_MISMATCH,
                                  _edit(ctx_fn=_dest(map_revision="synthetic-map-v2"))),
        "units-mismatch": ("Destination reports length in millimetres.", R.UNITS_MISMATCH,
                           _edit(ctx_fn=_dest(units={"length": "mm", "angle": "rad", "time": "s"}))),
        "missing-capability": ("Destination lacks report_status.", R.MISSING_CAPABILITY,
                               _edit(ctx_fn=_dest(capabilities=["inspect_waypoint"]))),
        "missing-sensor": ("Destination has no camera_front.", R.MISSING_SENSOR,
                           _edit(ctx_fn=_dest(sensors=sensors[:1]))),
        "sensor-type-mismatch": ("front_range exists but is a different sensor type.", R.SENSOR_TYPE_MISMATCH,
                                 _edit(ctx_fn=_dest(sensors=[{"name": "front_range", "type": "sonar", "units": "m"},
                                                             sensors[1]]))),
        "sensor-units-mismatch": ("front_range reports millimetres, mission expects metres.",
                                  R.SENSOR_UNITS_MISMATCH,
                                  _edit(ctx_fn=_dest(sensors=[{"name": "front_range", "type": "range", "units": "mm"},
                                                              sensors[1]]))),
        "action-command-unsupported": ("Destination cannot execute navigate_to_waypoint.",
                                       R.ACTION_COMMAND_UNSUPPORTED,
                                       _edit(ctx_fn=_dest(actions=[{"command": "set_joint_targets",
                                                                    "space": "joint_position_target", "units": "rad"}]))),
        "action-space-mismatch": ("Command exists but in a different action space.", R.ACTION_SPACE_MISMATCH,
                                  _edit(ctx_fn=_dest(actions=[{"command": "navigate_to_waypoint",
                                                               "space": "velocity_command", "units": "m"}]))),
        "action-units-mismatch": ("Action space matches but its units differ.", R.ACTION_UNITS_MISMATCH,
                                  _edit(ctx_fn=_dest(actions=[{"command": "navigate_to_waypoint",
                                                               "space": "waypoint_goal", "units": "cm"}]))),
        "multiple-incompatibilities": ("Several mismatches at once; the first in documented order is reported.",
                                       R.UNITS_MISMATCH,
                                       _edit(ctx_fn=_dest(units={"length": "mm", "angle": "rad", "time": "s"},
                                                          capabilities=["inspect_waypoint"]))),
    }


def bundle_fixture(name: str) -> dict[str, Any]:
    description, reason, build = bundle_cases()[name]
    bundle, ctx = build()
    return {"fixture_kind": "bundle-check", "synthetic": True, "name": name, "description": description,
            "expect": {"ok": reason is None, "reason": reason}, "context": ctx, "bundle": bundle}


# --------------------------------------------------------------------------- scripts
def op(name: str, expect: str | None = None, **kw: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"op": name, **kw}
    if expect is not None:
        out["expect"] = expect
    return out


def step(who: str, expect: str = "ACCEPTED", times: int = 1) -> list[dict[str, Any]]:
    return [op("step", expect, executor=who) for _ in range(times)]


def setup(**kw: Any) -> dict[str, Any]:
    base = {"task_id": TASK, "steps": list(STEPS), "requirements": copy.deepcopy(REQUIREMENTS),
            "initial_owner": "cloud-01", "lease_ticks": 50, "bundle_ttl": 10,
            "executors": [profile("cloud-01"), profile("edge-01"),
                          profile("edge-mm", sensors=[{"name": "front_range", "type": "range", "units": "mm"},
                                                      REQUIREMENTS["sensors"][1]])]}
    base.update(kw)
    return base


def effect(who: str, epoch: int, seq: int, step_id: str, eid: str) -> dict[str, Any]:
    return {"executor": who, "epoch": epoch, "effect_seq": seq, "effect_id": eid, "step": step_id}


def script_cases() -> dict[str, tuple[str, list[dict[str, Any]], dict[str, Any]]]:
    all5 = list(STEPS)
    return {
        "handoff-happy-path": (
            "Cloud-named executor completes two steps, hands off, edge-named executor finishes; origin self-fences.",
            step("cloud-01", times=2) + [op("handoff", "COMPLETED", to="edge-01")]
            + step("cloud-01", "SELF_FENCED") + step("edge-01", times=3) + step("edge-01", "NOTHING_LEFT"),
            {"owner": "edge-01", "epoch": 2, "completed": all5, "duplicate_effects_in_ledger": 0}),
        "stale-executor-after-takeover": (
            "The fence notice never reaches the origin. It resumes under its old epoch and is rejected; "
            "replayed effect, replayed bundle and stale renewal are rejected too.",
            step("cloud-01", times=2) + [op("handoff", "COMPLETED", to="edge-01", deliver_fence=False)]
            + step("cloud-01", "STALE_EXECUTOR") + step("edge-01")
            + [op("replay_effect", "REPLAYED_EFFECT", executor="edge-01"),
               op("replay_bundle", "REJECTED:REPLAYED_NONCE"),
               op("renew", "STALE_EXECUTOR", executor="cloud-01")],
            {"owner": "edge-01", "epoch": 2, "completed": all5[:3], "duplicate_effects_in_ledger": 0}),
        "effect-gate-rejections": (
            "Forged or malformed effects submitted straight to the sink after a takeover.",
            step("cloud-01") + [op("handoff", "COMPLETED", to="edge-01")] + step("edge-01")
            + [op("raw_effect", "EFFECT_SEQUENCE_GAP", effect=effect("edge-01", 2, 2, "wp-03", "forged-gap-01")),
               op("raw_effect", "EFFECT_SEQUENCE_REGRESSION", effect=effect("edge-01", 2, 0, "wp-03", "forged-regress-01")),
               op("raw_effect", "WRONG_NEXT_STEP", effect=effect("edge-01", 2, 1, "wp-05", "forged-step-01")),
               op("raw_effect", "UNKNOWN_EPOCH", effect=effect("edge-01", 9, 1, "wp-03", "forged-epoch-01")),
               op("raw_effect", "NOT_STATE_OWNER", effect=effect("edge-mm", 2, 1, "wp-03", "forged-owner-01")),
               op("raw_effect", "STALE_EXECUTOR", effect=effect("cloud-01", 1, 1, "wp-03", "forged-stale-01")),
               op("raw_effect", "MALFORMED_EFFECT", effect={"executor": "edge-01"}),
               op("raw_effect", "ACCEPTED", effect=effect("edge-01", 2, 1, "wp-03", "legit-after-forgeries"))],
            {"owner": "edge-01", "epoch": 2, "completed": all5[:3], "duplicate_effects_in_ledger": 0}),
        "lease-expiry-and-renewal": (
            "A lease must be renewed before it expires; after expiry the owner is rejected and cannot renew.",
            step("cloud-01") + [op("tick", n=40), op("renew", "RENEWED", executor="cloud-01"), op("tick", n=40)]
            + step("cloud-01") + [op("tick", n=20)] + step("cloud-01", "LEASE_EXPIRED")
            + [op("renew", "LEASE_EXPIRED", executor="cloud-01")],
            {"owner": "cloud-01", "epoch": 1, "completed": all5[:2], "duplicate_effects_in_ledger": 0}),
        "rollback-destination-crash": (
            "Destination crashes before activating. Ownership is re-issued to the origin at a NEW epoch (3).",
            step("cloud-01", times=2) + [op("handoff", "ROLLED_BACK", to="edge-01", fault="destination_crash")]
            + step("edge-01", "SELF_FENCED")
            + [op("raw_effect", "STALE_EXECUTOR", effect=effect("edge-01", 2, 0, "wp-03", "late-edge-01"))]
            + step("cloud-01", times=3),
            {"owner": "cloud-01", "epoch": 3, "completed": all5, "duplicate_effects_in_ledger": 0}),
        "rollback-ack-lost-after-effects": (
            "Destination activated and committed two steps but its acknowledgement was lost. Rollback resumes "
            "the origin from the sink ledger (cursor 3), not from the stale bundle cursor (1); the destination "
            "is then fenced.",
            step("cloud-01") + [op("handoff", "ROLLED_BACK", to="edge-01", fault="ack_lost", steps_before_ack_loss=2)]
            + step("edge-01", "STALE_EXECUTOR") + step("cloud-01", times=2),
            {"owner": "cloud-01", "epoch": 3, "completed": all5, "duplicate_effects_in_ledger": 0}),
        "park-origin-unavailable": (
            "Activation fails and the origin cannot take the mission back. Fail closed: nobody owns it.",
            step("cloud-01", times=2)
            + [op("handoff", "PARKED", to="edge-01", fault="destination_crash", origin_available=False)]
            + step("cloud-01", "SELF_FENCED")
            + [op("raw_effect", "STALE_EXECUTOR", effect=effect("cloud-01", 1, 2, "wp-03", "zombie-cloud-01")),
               op("raw_effect", "NOT_STATE_OWNER", effect=effect("cloud-01", 3, 0, "wp-03", "claim-cloud-01")),
               op("handoff", "REJECTED:NOT_STATE_OWNER", to="edge-01")],
            {"owner": None, "epoch": 3, "completed": all5[:2], "duplicate_effects_in_ledger": 0}),
        "park-by-policy": (
            "The bundle's rollback policy is 'park': a failed activation parks the mission even if the origin is up.",
            step("cloud-01") + [op("handoff", "PARKED", to="edge-01", fault="destination_crash", on_failure="park")]
            + step("cloud-01", "SELF_FENCED"),
            {"owner": None, "epoch": 3, "completed": all5[:1], "duplicate_effects_in_ledger": 0}),
        "abort-destination-unreachable": (
            "Destination unreachable during validation: nothing is committed, origin keeps its epoch and may retry.",
            step("cloud-01", times=2) + [op("handoff", "ABORTED", to="edge-01", fault="destination_unreachable")]
            + step("cloud-01") + [op("handoff", "COMPLETED", to="edge-01")] + step("edge-01", times=2),
            {"owner": "edge-01", "epoch": 2, "completed": all5, "duplicate_effects_in_ledger": 0}),
        "incompatible-destination-refused": (
            "A destination reporting a sensor in different units is refused; the origin keeps going. "
            "Handing off a finished mission is refused as well.",
            step("cloud-01", times=2) + [op("handoff", "REJECTED:SENSOR_UNITS_MISMATCH", to="edge-mm")]
            + step("cloud-01", times=3) + [op("handoff", "REJECTED:MISSION_COMPLETE", to="edge-01")],
            {"owner": "cloud-01", "epoch": 1, "completed": all5, "duplicate_effects_in_ledger": 0}),
        "ping-pong-handoffs": (
            "Two successive handoffs (cloud to edge and back) advance the epoch twice and keep the ledger gap-free.",
            step("cloud-01") + [op("handoff", "COMPLETED", to="edge-01")] + step("edge-01")
            + [op("handoff", "COMPLETED", to="cloud-01")] + step("cloud-01", times=3)
            + step("edge-01", "SELF_FENCED"),
            {"owner": "cloud-01", "epoch": 3, "completed": all5, "duplicate_effects_in_ledger": 0}),
    }


def script_fixture(name: str) -> dict[str, Any]:
    description, ops, final = script_cases()[name]
    return {"fixture_kind": "handoff-script", "synthetic": True, "name": name, "description": description,
            "setup": setup(), "ops": ops, "expect_final": final}


def all_fixtures() -> dict[Path, dict[str, Any]]:
    out: dict[Path, dict[str, Any]] = {}
    for n in bundle_cases():
        out[BUNDLE_DIR / f"{n}.json"] = bundle_fixture(n)
    for n in script_cases():
        out[SCRIPT_DIR / f"{n}.json"] = script_fixture(n)
    return out


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify committed fixtures match the generator")
    args = parser.parse_args(argv)
    fixtures = all_fixtures()
    if args.check:
        wanted = {p for p in fixtures}
        present = set(BUNDLE_DIR.glob("*.json")) | set(SCRIPT_DIR.glob("*.json"))
        drift = [p.name for p, d in fixtures.items() if not p.exists() or p.read_text(encoding="utf-8") != render(d)]
        extra = sorted(p.name for p in present - wanted)
        if drift or extra:
            print(f"fixture drift: changed/missing={drift} unexpected={extra}", file=sys.stderr)
            return 1
        print(f"{len(fixtures)} fixtures match the generator")
        return 0
    for p, d in fixtures.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render(d), encoding="utf-8")
    print(f"wrote {len(fixtures)} fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
