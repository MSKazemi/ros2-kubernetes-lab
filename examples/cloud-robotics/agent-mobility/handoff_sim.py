#!/usr/bin/env python3
"""Deterministic mission-state handoff SIMULATOR (SYNTHETIC, non-actuating, single process).

Models, with logical ticks only:
  * a coordinator that owns (state_owner, epoch) and consumes handoff nonces/sequences,
  * a simulated effect sink that is the authoritative ledger and enforces the epoch fence,
  * executors that may be stale ("zombies") after a takeover,
  * rollback when a committed handoff fails to activate.

Nothing here moves a process, a container or a model, and nothing is sent to a robot or
ROS 2. The sink only appends records to an in-memory list. There is no clock, no randomness
and no network, so every run is reproducible. Ticks are logical, not milliseconds.
It is NOT a trust boundary: coordinator, sink and executors share one Python process.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import mission_state as ms
from mission_state import Reason, Rejection

HERE = Path(__file__).resolve().parent
SCRIPT_DIR = HERE / "fixtures" / "scripts"
SIM_KIND = "handoff-script"

OUTCOMES = ("COMPLETED", "ABORTED", "REJECTED", "ROLLED_BACK", "PARKED")
FAULTS = (None, "destination_unreachable", "destination_crash", "ack_lost")


# --------------------------------------------------------------------------- sink
class EffectSink:
    """Simulated, non-actuating effect gate and authoritative effect ledger."""

    def __init__(self, steps: list[str]):
        self.steps = list(steps)
        self.ledger: list[dict[str, Any]] = []
        self.accepted_ids: set[str] = set()
        self.epoch = 0
        self.owner: str | None = None
        self.lease_expires_tick = 0
        self.last_seq = -1

    def install_grant(self, owner: str | None, epoch: int, lease_expires_tick: int) -> None:
        """Coordinator publishes a new grant. The sink refuses to go backwards (internal invariant)."""
        if type(epoch) is not int or epoch <= self.epoch:
            raise ValueError(f"grant epoch {epoch} must exceed sink epoch {self.epoch}")
        self.owner, self.epoch, self.lease_expires_tick, self.last_seq = owner, epoch, lease_expires_tick, -1

    def extend_lease(self, lease_expires_tick: int) -> None:
        self.lease_expires_tick = max(self.lease_expires_tick, lease_expires_tick)

    def submit(self, effect: Any, now_tick: int) -> str:
        """Return ``"ACCEPTED"`` or a :class:`Reason` value. Never raises on bad input."""
        keys = {"executor", "epoch", "effect_seq", "effect_id", "step"}
        if (not isinstance(effect, dict) or set(effect) != keys
                or not all(isinstance(effect[k], str) and ms.ID_RE.fullmatch(effect[k])
                           for k in ("executor", "effect_id", "step"))
                or not all(type(effect[k]) is int and effect[k] >= 0 for k in ("epoch", "effect_seq"))):
            return Reason.MALFORMED_EFFECT
        if effect["epoch"] < self.epoch:
            return Reason.STALE_EXECUTOR
        if effect["epoch"] > self.epoch:
            return Reason.UNKNOWN_EPOCH
        if self.owner is None or effect["executor"] != self.owner:
            return Reason.NOT_STATE_OWNER
        if now_tick > self.lease_expires_tick:
            return Reason.LEASE_EXPIRED
        if effect["effect_id"] in self.accepted_ids:
            return Reason.REPLAYED_EFFECT
        if effect["effect_seq"] < self.last_seq + 1:
            return Reason.EFFECT_SEQUENCE_REGRESSION
        if effect["effect_seq"] > self.last_seq + 1:
            return Reason.EFFECT_SEQUENCE_GAP
        if len(self.ledger) >= len(self.steps) or effect["step"] != self.steps[len(self.ledger)]:
            return Reason.WRONG_NEXT_STEP
        self.ledger.append({"step": effect["step"], "effect_id": effect["effect_id"],
                            "executor": effect["executor"], "epoch": effect["epoch"], "tick": now_tick})
        self.accepted_ids.add(effect["effect_id"])
        self.last_seq = effect["effect_seq"]
        return "ACCEPTED"

    @property
    def effect_ids(self) -> tuple[str, ...]:
        return tuple(e["effect_id"] for e in self.ledger)

    @property
    def completed(self) -> list[str]:
        return [e["step"] for e in self.ledger]


# --------------------------------------------------------------------------- executor
class Executor:
    """An executor's *belief* about its authority. It can be stale; the sink is the judge."""

    def __init__(self, profile: dict[str, Any]):
        self.profile = ms.validate_profile(profile)
        self.id = self.profile["executor_id"]
        self.active = False
        self.epoch = 0
        self.next_seq = 0
        self.last_effect: dict[str, Any] | None = None

    def activate(self, epoch: int) -> None:
        self.active, self.epoch, self.next_seq = True, epoch, 0

    def fence(self) -> None:
        self.active = False

    def build_effect(self, task_id: str, step: str) -> dict[str, Any]:
        return {"executor": self.id, "epoch": self.epoch, "effect_seq": self.next_seq,
                "effect_id": f"{task_id}-{self.id}-e{self.epoch}-s{self.next_seq}", "step": step}


# --------------------------------------------------------------------------- simulator
class HandoffSimulator:
    def __init__(self, *, task_id: str, steps: list[str], requirements: dict[str, Any],
                 profiles: list[dict[str, Any]], initial_owner: str, lease_ticks: int = 50,
                 bundle_ttl: int = 10, mission_revision: int = 1):
        self.task_id, self.steps, self.requirements = task_id, list(steps), requirements
        self.mission_revision, self.lease_ticks, self.bundle_ttl = mission_revision, lease_ticks, bundle_ttl
        self.executors = {p["executor_id"]: Executor(p) for p in profiles}
        if initial_owner not in self.executors:
            raise ValueError("initial_owner must be one of the executors")
        self.now = 0
        self.owner: str | None = initial_owner
        self.epoch = 1
        self.last_sequence = 0
        self.seen_nonces: set[str] = set()
        self.sink = EffectSink(steps)
        self.sink.install_grant(initial_owner, 1, self.now + lease_ticks)
        self.executors[initial_owner].activate(1)
        self.lease_expires_tick = self.now + lease_ticks
        self.handoff_counter = 0
        self.last_bundle: dict[str, Any] | None = None
        self.trace: list[dict[str, Any]] = []

    # -- time and logging
    def tick(self, n: int = 1) -> None:
        self.now += n

    def _log(self, event: str, **data: Any) -> None:
        self.trace.append({"tick": self.now, "event": event, **data})

    # -- executor-side work
    def step(self, executor_id: str) -> str:
        """The named executor tries to commit the next mission step using ITS OWN belief."""
        ex = self.executors[executor_id]
        if not ex.active:
            self._log("step", executor=executor_id, verdict="SELF_FENCED")
            return "SELF_FENCED"
        done = len(self.sink.ledger)
        if done >= len(self.steps):
            self._log("step", executor=executor_id, verdict="NOTHING_LEFT")
            return "NOTHING_LEFT"
        effect = ex.build_effect(self.task_id, self.steps[done])
        verdict = self.sink.submit(effect, self.now)
        if verdict == "ACCEPTED":
            ex.next_seq += 1
            ex.last_effect = effect
        self._log("step", executor=executor_id, epoch=effect["epoch"], effect_id=effect["effect_id"],
                  step=effect["step"], verdict=verdict)
        return verdict

    def replay_last_effect(self, executor_id: str) -> str:
        ex = self.executors[executor_id]
        if ex.last_effect is None:
            return "NOTHING_TO_REPLAY"
        verdict = self.sink.submit(dict(ex.last_effect), self.now)
        self._log("replay_effect", executor=executor_id, effect_id=ex.last_effect["effect_id"], verdict=verdict)
        return verdict

    def raw_effect(self, effect: Any) -> str:
        """Submit an arbitrary (possibly forged or malformed) effect straight to the sink."""
        verdict = self.sink.submit(effect, self.now)
        self._log("raw_effect", verdict=verdict)
        return verdict

    def renew(self, executor_id: str, epoch: int | None = None) -> str:
        ex = self.executors[executor_id]
        claimed = ex.epoch if epoch is None else epoch
        if claimed < self.epoch:
            verdict = Reason.STALE_EXECUTOR
        elif executor_id != self.owner:
            verdict = Reason.NOT_STATE_OWNER
        elif self.now > self.lease_expires_tick:
            verdict = Reason.LEASE_EXPIRED
        else:
            self.lease_expires_tick = self.now + self.lease_ticks
            self.sink.extend_lease(self.lease_expires_tick)
            verdict = "RENEWED"
        self._log("renew", executor=executor_id, verdict=verdict)
        return verdict

    # -- handoff
    def build_bundle(self, to_executor: str, *, on_failure: str = "reissue_to_origin") -> dict[str, Any]:
        if self.owner is None:
            raise Rejection(Reason.NOT_STATE_OWNER, "owner", "mission is parked; nobody owns it")
        self.handoff_counter += 1
        cursor = len(self.sink.ledger)
        n = self.handoff_counter
        bundle = {
            "schema": ms.SCHEMA, "simulated": True,
            "mission": {"task_id": self.task_id, "mission_revision": self.mission_revision, "steps": list(self.steps)},
            "progress": {"cursor": cursor, "completed": self.sink.completed[:],
                         "committed_effect_ids": list(self.sink.effect_ids)},
            "ownership": {"state_owner": self.owner, "epoch": self.epoch,
                          "lease_expires_tick": self.lease_expires_tick},
            "handoff": {"handoff_id": f"{self.task_id}-h{n:03d}", "nonce": f"nonce-{self.task_id}-{n:04d}"[:64],
                        "sequence": self.last_sequence + 1, "from_executor": self.owner,
                        "to_executor": to_executor, "issued_tick": self.now,
                        "expires_tick": self.now + self.bundle_ttl},
            "requirements": json.loads(json.dumps(self.requirements)),
            "rollback": {"on_failure": on_failure, "origin_executor": self.owner, "resume_from": "effect_ledger"},
        }
        return ms.seal(bundle)

    def _context(self, destination: dict[str, Any]) -> ms.CommitContext:
        return ms.CommitContext(now_tick=self.now, owner=self.owner, epoch=self.epoch,
                                last_sequence=self.last_sequence, seen_nonces=frozenset(self.seen_nonces),
                                ledger_effect_ids=self.sink.effect_ids, destination=destination)

    def handoff(self, to_executor: str, *, fault: str | None = None, deliver_fence: bool = True,
                steps_before_ack_loss: int = 0, origin_available: bool = True,
                on_failure: str = "reissue_to_origin") -> dict[str, Any]:
        try:
            bundle = self.build_bundle(to_executor, on_failure=on_failure)
        except Rejection as exc:
            return self._result("REJECTED", exc.reason)
        return self.submit_bundle(bundle, fault=fault, deliver_fence=deliver_fence,
                                  steps_before_ack_loss=steps_before_ack_loss, origin_available=origin_available)

    def replay_last_bundle(self) -> dict[str, Any]:
        if self.last_bundle is None:
            return self._result("REJECTED", "NOTHING_TO_REPLAY")
        return self.submit_bundle(self.last_bundle)

    def submit_bundle(self, bundle: Any, *, fault: str | None = None, deliver_fence: bool = True,
                      steps_before_ack_loss: int = 0, origin_available: bool = True) -> dict[str, Any]:
        if fault not in FAULTS:
            raise ValueError(f"unknown fault {fault!r}")
        to = bundle.get("handoff", {}).get("to_executor") if isinstance(bundle, dict) else None
        dest = self.executors.get(to)
        if dest is None:
            return self._result("REJECTED", Reason.WRONG_DESTINATION)
        # PREPARE happened at the origin when the bundle was built; VALIDATE runs here.
        try:
            doc = ms.validate_for_commit(bundle, self._context(dest.profile))
        except Rejection as exc:
            self._log("validate", result="REJECTED", reason=exc.reason, field=exc.field)
            return self._result("REJECTED", exc.reason)
        if isinstance(bundle, dict):
            self.last_bundle = bundle
        if fault == "destination_unreachable":
            self._log("abort", reason="destination_unreachable", note="nothing committed; origin retains ownership")
            return self._result("ABORTED", "destination_unreachable")
        # COMMIT: consume nonce/sequence, bump epoch, publish the grant to the sink.
        origin = self.executors[doc["handoff"]["from_executor"]]
        self.seen_nonces.add(doc["handoff"]["nonce"])
        self.last_sequence = doc["handoff"]["sequence"]
        self.epoch += 1
        self.owner = dest.id
        self.lease_expires_tick = self.now + self.lease_ticks
        self.sink.install_grant(dest.id, self.epoch, self.lease_expires_tick)
        if deliver_fence:
            origin.fence()
        self._log("commit", owner=dest.id, epoch=self.epoch, nonce=doc["handoff"]["nonce"],
                  fence_delivered_to_origin=deliver_fence)
        # ACTIVATE
        if fault is None:
            dest.activate(self.epoch)
            self._log("activate", executor=dest.id, epoch=self.epoch)
            return self._result("COMPLETED", None)
        if fault == "ack_lost":
            dest.activate(self.epoch)  # destination really started; only the acknowledgement was lost
            for _ in range(steps_before_ack_loss):
                self.step(dest.id)
        self._log("activation_failed", fault=fault, executor=dest.id)
        return self._rollback(doc, origin, origin_available)

    def _rollback(self, doc: dict[str, Any], origin: Executor, origin_available: bool) -> dict[str, Any]:
        """New higher-epoch grant to the origin (or to nobody). The epoch is never decremented."""
        policy = doc["rollback"]["on_failure"]
        self.epoch += 1
        if policy == "reissue_to_origin" and origin_available:
            self.owner = origin.id
            self.lease_expires_tick = self.now + self.lease_ticks
            self.sink.install_grant(origin.id, self.epoch, self.lease_expires_tick)
            origin.activate(self.epoch)
            self._log("rollback", owner=origin.id, epoch=self.epoch, resume_cursor=len(self.sink.ledger),
                      resume_from="effect_ledger")
            return self._result("ROLLED_BACK", "activation_failed")
        self.owner = None
        self.sink.install_grant(None, self.epoch, self.now)
        self._log("parked", epoch=self.epoch, why="policy_park" if policy == "park" else "origin_unavailable")
        return self._result("PARKED", "activation_failed")

    def _result(self, outcome: str, reason: str | None) -> dict[str, Any]:
        assert outcome in OUTCOMES
        verdict = outcome if reason is None or outcome in ("ABORTED", "ROLLED_BACK", "PARKED") else f"{outcome}:{reason}"
        return {"outcome": outcome, "reason": reason, "verdict": verdict, "owner": self.owner, "epoch": self.epoch}


# --------------------------------------------------------------------------- scripts
def simulator_from_setup(setup: dict[str, Any]) -> HandoffSimulator:
    return HandoffSimulator(task_id=setup["task_id"], steps=setup["steps"], requirements=setup["requirements"],
                            profiles=setup["executors"], initial_owner=setup["initial_owner"],
                            lease_ticks=setup.get("lease_ticks", 50), bundle_ttl=setup.get("bundle_ttl", 10))


def run_script(script: dict[str, Any]) -> dict[str, Any]:
    """Execute one handoff-script fixture. Returns a report; ``ok`` is True iff every expectation held."""
    if script.get("fixture_kind") != SIM_KIND or script.get("synthetic") is not True:
        raise ValueError("not a synthetic handoff-script fixture")
    sim = simulator_from_setup(script["setup"])
    results = []
    for index, op in enumerate(script["ops"]):
        name = op["op"]
        if name == "tick":
            sim.tick(op["n"])
            continue
        if name == "step":
            got = sim.step(op["executor"])
        elif name == "replay_effect":
            got = sim.replay_last_effect(op["executor"])
        elif name == "raw_effect":
            got = sim.raw_effect(op["effect"])
        elif name == "renew":
            got = sim.renew(op["executor"], op.get("epoch"))
        elif name == "handoff":
            got = sim.handoff(op["to"], fault=op.get("fault"), deliver_fence=op.get("deliver_fence", True),
                              steps_before_ack_loss=op.get("steps_before_ack_loss", 0),
                              origin_available=op.get("origin_available", True),
                              on_failure=op.get("on_failure", "reissue_to_origin"))["verdict"]
        elif name == "replay_bundle":
            got = sim.replay_last_bundle()["verdict"]
        else:
            raise ValueError(f"unknown op {name!r}")
        results.append({"index": index, "op": name, "expected": op["expect"], "got": got,
                        "ok": got == op["expect"]})
    final = {"owner": sim.owner, "epoch": sim.epoch, "completed": sim.sink.completed,
             "duplicate_effects_in_ledger": len(sim.sink.effect_ids) - len(set(sim.sink.effect_ids))}
    final_ok = all(final.get(k) == v for k, v in script["expect_final"].items())
    return {"name": script["name"], "simulation": True, "synthetic": True, "non_actuating": True,
            "time_unit": "logical_tick", "ops": results, "final": final, "final_ok": final_ok,
            "ok": final_ok and all(r["ok"] for r in results), "trace": sim.trace}


def expected_reasons(script: dict[str, Any]) -> set[str]:
    """Reason codes a script expects (used by the coverage test)."""
    found: set[str] = set()
    for op in script["ops"]:
        exp = op.get("expect")
        if isinstance(exp, str):
            found.add(exp.split(":", 1)[1] if ":" in exp else exp)
    return found & Reason.all()


def load_scripts(directory: Path = SCRIPT_DIR) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scripts", nargs="*", type=Path, help="handoff-script fixtures (default: fixtures/scripts/*.json)")
    parser.add_argument("--trace", action="store_true", help="include the full event trace in the output")
    args = parser.parse_args(argv)
    try:
        paths = args.scripts or sorted(SCRIPT_DIR.glob("*.json"))
        reports = [run_script(json.loads(p.read_text(encoding="utf-8"))) for p in paths]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"handoff_sim: invalid input: {exc}", file=sys.stderr)
        return 2
    for rep in reports:
        if not args.trace:
            rep = {k: v for k, v in rep.items() if k != "trace"}
        print(json.dumps(rep, sort_keys=True))
    return 0 if all(r["ok"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
