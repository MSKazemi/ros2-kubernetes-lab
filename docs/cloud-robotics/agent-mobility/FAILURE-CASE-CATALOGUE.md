# Failure-case catalogue

> **SIMULATION / SYNTHETIC.** Each row says what the offline toy does for a failure, which fixture demonstrates it, and what is **not** covered. "Expected behaviour" is a software assertion in unit tests, not an observation of a real system. Fixture directories: [`fixtures/bundles/`](../../../examples/cloud-robotics/agent-mobility/fixtures/bundles/) (`B:`) and [`fixtures/scripts/`](../../../examples/cloud-robotics/agent-mobility/fixtures/scripts/) (`S:`).

## 1. Covered by the simulator (every row has a test)

| ID | Failure | Expected behaviour | Reason / outcome | Fixture |
| --- | --- | --- | --- | --- |
| FC-01 | Bundle is not an object, or a field is missing or unknown | Refuse before anything else | `MALFORMED_DOCUMENT`, `MISSING_FIELD`, `UNKNOWN_FIELD` | B: `malformed-document`, `missing-field`, `unknown-field` |
| FC-02 | Wrong type, out-of-range value or bad identifier | Refuse | `WRONG_TYPE`, `BAD_VALUE`, `BAD_IDENTIFIER` | B: `wrong-type`, `bad-value`, `bad-identifier`, `handoff-not-an-object`, `destination-is-a-list` |
| FC-03 | Unknown schema version, or non-simulated document | Refuse | `UNSUPPORTED_SCHEMA_VERSION`, `NOT_SIMULATED` | B: `unsupported-schema-version`, `not-simulated` |
| FC-04 | Content altered after sealing | Refuse (accidental-change detection only) | `DIGEST_MISMATCH` | B: `digest-mismatch` |
| FC-05 | Progress claims inconsistent (`completed` is not the step prefix) or owner fields disagree | Refuse | `PROGRESS_INCONSISTENT`, `INCONSISTENT_BUNDLE` | B: `progress-inconsistent`, `inconsistent-bundle` |
| FC-06 | Bundle too old, or from the future (disagreeing clocks) | Refuse | `BUNDLE_EXPIRED`, `BUNDLE_FROM_FUTURE` | B: `bundle-expired`, `bundle-from-future` |
| FC-07 | Source equals destination, or bundle addressed to another executor | Refuse | `SAME_EXECUTOR`, `WRONG_DESTINATION` | B: `same-executor`, `wrong-destination` |
| FC-08 | Same bundle submitted twice | Second refused, state unchanged | `REPLAYED_NONCE` | B: `replayed-nonce`; S: `stale-executor-after-takeover` |
| FC-09 | Fresh nonce, old sequence | Refuse | `STALE_SEQUENCE` | B: `stale-sequence` |
| FC-10 | Bundle sealed before another handoff advanced the epoch | Refuse | `STALE_EPOCH` | B: `stale-epoch` |
| FC-11 | Sender is not the state owner | Refuse | `WRONG_STATE_OWNER` | B: `wrong-state-owner` |
| FC-12 | Checkpoint lags the authoritative ledger | Refuse | `STALE_CHECKPOINT` | B: `stale-checkpoint` |
| FC-13 | Nothing left to hand off | Refuse | `MISSION_COMPLETE` | B: `mission-complete`; S: `incompatible-destination-refused` |
| FC-14 | Destination differs in schema, class, frame, map, units, capability, sensor, or action space | Refuse; origin keeps the mission; **no silent adaptation** | `SCHEMA_NOT_SUPPORTED`, `ROBOT_CLASS_MISMATCH`, `FRAME_MISMATCH`, `MAP_REVISION_MISMATCH`, `UNITS_MISMATCH`, `MISSING_CAPABILITY`, `MISSING_SENSOR`, `SENSOR_TYPE_MISMATCH`, `SENSOR_UNITS_MISMATCH`, `ACTION_COMMAND_UNSUPPORTED`, `ACTION_SPACE_MISMATCH`, `ACTION_UNITS_MISMATCH` | B: one fixture per code; S: `incompatible-destination-refused` |
| FC-15 | Old-epoch executor resumes after takeover (fence notice lost) | Effect refused; ledger unchanged | `STALE_EXECUTOR` | S: `stale-executor-after-takeover` |
| FC-16 | Retransmitted effect | Refused, no duplicate in ledger | `REPLAYED_EFFECT` | S: `stale-executor-after-takeover` |
| FC-17 | Sequence gap, regression, wrong step, unknown epoch, non-owner, malformed effect | Each refused with its own code | `EFFECT_SEQUENCE_GAP`, `EFFECT_SEQUENCE_REGRESSION`, `WRONG_NEXT_STEP`, `UNKNOWN_EPOCH`, `NOT_STATE_OWNER`, `MALFORMED_EFFECT` | S: `effect-gate-rejections` |
| FC-18 | Lease expires; late renewal | Effects and renewal refused | `LEASE_EXPIRED` | S: `lease-expiry-and-renewal` |
| FC-19 | Destination unreachable before commit | **ABORTED**; epoch, nonce, sequence unchanged; origin may retry with a new bundle | `ABORTED` | S: `abort-destination-unreachable` |
| FC-20 | Destination crashes after commit, before activation | **ROLLED_BACK** with a new higher epoch to the origin; destination fenced | `ROLLED_BACK` | S: `rollback-destination-crash` |
| FC-21 | Destination activates and commits steps, acknowledgement lost | **ROLLED_BACK**; origin resumes from the *ledger*, destination's committed effects kept, destination fenced | `ROLLED_BACK`, then `STALE_EXECUTOR` | S: `rollback-ack-lost-after-effects` |
| FC-22 | Rollback impossible (origin unavailable) or policy is `park` | **PARKED**: no owner, all effects refused (fail closed) | `PARKED`, `NOT_STATE_OWNER` | S: `park-origin-unavailable`, `park-by-policy` |
| FC-23 | Repeated handoffs (A to B to A) | Epoch increases each time; ledger gap-free; fenced executor self-fences | `COMPLETED` | S: `ping-pong-handoffs` |
| FC-24 | Bundle of any malformed JSON shape (null, string, list, `handoff` not an object, unhashable destination, wrong nested types) | Typed `REJECTED` result, no exception; owner, epoch, sequence, nonces, ledger and executor beliefs unchanged | one of the shape reasons (`MALFORMED_DOCUMENT`, `MISSING_FIELD`, `WRONG_TYPE`, `BAD_VALUE`, `BAD_IDENTIFIER`, `UNSUPPORTED_SCHEMA_VERSION`, `NOT_SIMULATED`) or `WRONG_DESTINATION` for an unknown executor | `MalformedBundleTests` (40 cases) in `tests/test_handoff_sim.py`; B: `handoff-not-an-object`, `destination-is-a-list` |
| FC-25 | Simulator-derived identifiers for an awkward but valid `task_id` (contains `.` or `:`, 60 to 64 characters, or differs from another id only in the part that must be cut) | Derived `handoff_id`, `nonce` and `effect_id` always satisfy the validator's patterns and the 64-character limit; sanitised or truncated text gets a stable 8-hex hash suffix, the counter is appended after it and never cut; five consecutive handoffs never produce `REPLAYED_NONCE` | `COMPLETED` | `IdDerivationTests` in `tests/test_handoff_sim.py` |
| FC-26 | Malformed script input: a `tick` that is negative, fractional, boolean, string, null, or above `MAX_TICKS` (10^9); unknown ops or keys; unknown executors; bad fault, policy or flag types; out-of-range `steps_before_ack_loss`; invalid setup | Rejected as a script error **before anything runs** (`ValueError`; CLI exit code 2). The logical clock only moves forward by an integer in `[0, 10^9]`, and `0` is an allowed no-op | exit code 2 (no verdict) | `ScriptValidationTests` in `tests/test_handoff_sim.py` |

## 2. Not covered (listed so the toy is not over-read)

| ID | Failure | Why it is out of scope here |
| --- | --- | --- |
| NC-01 | Coordinator or sink crash, restart, or split brain | State is in memory; needs durable linearizable grant storage |
| NC-02 | Forged bundle with a recomputed digest, impersonated executor | No signatures, MACs or authenticated transport |
| NC-03 | Real clock skew, jitter, timeouts | Only caller-supplied logical ticks |
| NC-04 | Network partition between coordinator and sink | Single process |
| NC-05 | Physical effect already emitted before fencing | No actuator; needs safe-stop and actuator-side checks (issue #59) |
| NC-06 | Effect acknowledged lost with uncertain external side effect needing reconciliation | Retransmission is modelled, executor-side reconcile is not |
| NC-07 | Observation staleness or malformed sensor data | Belongs to the observation/action contract (issue #55) |
| NC-08 | Calibration, intrinsics, dynamics or safety-limit mismatch | Only declared metadata is compared |
| NC-09 | Malicious profile (destination lies about capabilities) | No attestation |
| NC-10 | Cross-worker DDS delivery, Kubernetes rescheduling, ROS 2 QoS effects | Not run; depends on issues #14, #15, #16 |
| NC-11 | Performance: handoff time, downtime, bytes, success rate | Not measured; ticks are not milliseconds |
| NC-12 | Multi-mission or multi-robot concurrency | One mission, one ledger |

## 3. Adding a failure case

1. Name the failure and decide whether it is a *bundle* rejection (add a `Reason` and a `bundle-check` fixture in `fixture_gen.py`) or a *runtime* behaviour (add a `handoff-script` fixture).
2. Regenerate with `python3 fixture_gen.py`, commit the generated JSON, and run `python3 fixture_gen.py --check`.
3. The test suite fails if a `Reason` code has no fixture or if committed fixtures drift from the generator.
4. Add the row here, with its status as **covered** only if a test asserts it.
