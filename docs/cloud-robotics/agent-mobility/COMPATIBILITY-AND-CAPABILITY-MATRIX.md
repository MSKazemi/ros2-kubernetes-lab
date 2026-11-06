# Compatibility and capability matrix

> **SIMULATION.** Compatibility here means *declared* metadata matches. It is not a check that a real robot, sensor driver or controller behaves as declared, and the toy cannot verify that a profile is truthful.

A destination publishes a **profile** (what it declares it can do). A bundle carries **requirements** (what the mission needs). The validator ([`compatibility_violations`](../../../examples/cloud-robotics/agent-mobility/mission_state.py)) compares them; any mismatch refuses the handoff and the origin keeps the mission. Mismatches are **never** silently adapted (no unit conversion, no frame transform, no substitute sensor).

## 1. Profile shape

| Profile field | Type | Meaning |
| --- | --- | --- |
| `executor_id` | identifier | Must equal the bundle's `handoff.to_executor` (`WRONG_DESTINATION`) |
| `supported_schemas` | list of strings | Exact schema versions implemented |
| `robot_class` | identifier | Embodiment class (for example a differential-drive base versus a manipulator arm) |
| `frame_id`, `map_revision` | identifiers | Coordinate frame and map the destination localises in |
| `units` | `{length, angle, time}` | Unit convention of the destination's interfaces |
| `capabilities` | list | Named skills the destination offers |
| `sensors` | list of `{name, type, units}` | Sensor streams available |
| `actions` | list of `{command, space, units}` | Action interfaces offered |

## 2. Dimension by dimension

| # | Dimension | Requirement field | Profile field | Rule | Reason on mismatch | Fixture (`fixtures/bundles/`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Schema | `schema` | `supported_schemas` | Version is listed | `SCHEMA_NOT_SUPPORTED` | `schema-not-supported` |
| 2 | Embodiment | `robot_class` | `robot_class` | Equal | `ROBOT_CLASS_MISMATCH` | `robot-class-mismatch` |
| 3 | Frame | `frame_id` | `frame_id` | Equal | `FRAME_MISMATCH` | `frame-mismatch` |
| 4 | Map | `map_revision` | `map_revision` | Equal | `MAP_REVISION_MISMATCH` | `map-revision-mismatch` |
| 5 | Unit convention | `units.length/angle/time` | `units.*` | Each equal | `UNITS_MISMATCH` | `units-mismatch` |
| 6 | Capabilities | `capabilities` | `capabilities` | Requirement is a **subset** of the profile; extra capabilities are allowed | `MISSING_CAPABILITY` | `missing-capability` |
| 7 | Sensor present | `sensors[].name` | `sensors[].name` | Each required name exists | `MISSING_SENSOR` | `missing-sensor` |
| 8 | Sensor type | `sensors[].type` | `sensors[].type` | Equal per name | `SENSOR_TYPE_MISMATCH` | `sensor-type-mismatch` |
| 9 | Sensor units | `sensors[].units` | `sensors[].units` | Equal per name | `SENSOR_UNITS_MISMATCH` | `sensor-units-mismatch` |
| 10 | Action command | `action.command` | `actions[].command` | Destination offers the command | `ACTION_COMMAND_UNSUPPORTED` | `action-command-unsupported` |
| 11 | Action space | `action.space` | `actions[].space` | Offered for that command | `ACTION_SPACE_MISMATCH` | `action-space-mismatch` |
| 12 | Action units | `action.units` | `actions[].units` | Offered for that space | `ACTION_UNITS_MISMATCH` | `action-units-mismatch` |

Rows are evaluated top to bottom. All violations are collected, but the **first** is the reported reason (fixture `multiple-incompatibilities` shows `UNITS_MISMATCH` winning over a missing capability).

Why these dimensions matter, qualitatively: a destination that treats millimetres as metres, a different frame as the same frame, or a joint-position command as a velocity command would interpret the *same* mission cursor differently. Refusing is cheaper than discovering the disagreement after a simulated effect has been committed.

## 3. Worked example with the fixture executors (SYNTHETIC)

Mission requirements used by the fixtures: class `sim-mobile-base`, frame `map`, map `synthetic-map-v1`, units `m/rad/s`, capabilities `inspect_waypoint` and `report_status`, sensors `front_range` (type `range`, unit `m`) and `camera_front` (type `rgb_image`, unit `pixel`), action `navigate_to_waypoint` in space `waypoint_goal` with unit `m`.

| Executor profile | Differs from the requirements by | Handoff verdict in the simulator |
| --- | --- | --- |
| `cloud-01` | nothing (also offers an extra skill) | accepted (as a destination in the ping-pong script) |
| `edge-01` | nothing (also offers an extra skill) | accepted |
| `edge-mm` | `front_range` reports `mm` | `REJECTED:SENSOR_UNITS_MISMATCH`, origin keeps the mission (script `incompatible-destination-refused`) |

## 4. Deliberately NOT checked in v1

Each item below can make a real handoff unsafe or useless; v1 neither checks nor claims to check them.

| Not checked | Where it would belong |
| --- | --- |
| Observation freshness and schema of live sensor data | Observation/action contract ([`mock-policy`](../../../examples/cloud-robotics/mock-policy/README.md), issue #55) |
| Action limits, joint ranges, safe-stop behaviour | Fail-closed action gate (issue #59) |
| Calibration, extrinsics, camera intrinsics, sensor timing | Future embodiment profile |
| Compute, memory, model or policy version and weights | Model-relocation experiments (see [WHAT-IS-NOT-MOVED.md](WHAT-IS-NOT-MOVED.md)) |
| Network latency or bandwidth budgets | Placement experiments (issues #62, #85); no number is asserted here |
| Truthfulness of a profile (attestation) | Not provided; the toy trusts the declared profile |
| Permission to actuate | Separate authority decision; see [WHAT-IS-NOT-MOVED.md](WHAT-IS-NOT-MOVED.md) |

## 5. Extending the matrix

Add a dimension by (1) adding closed fields to the bundle and profile under a **new schema version** ([versioning](MISSION-STATE-SCHEMA.md#3-versioning)), (2) adding a distinct reason code, (3) appending it to `compatibility_violations` in a documented position, (4) adding a fixture that triggers only that reason. The test suite fails if a reason code has no fixture.
