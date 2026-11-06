# Portable mission-state schema `mission-state/v1`

> **SIMULATION.** A specification for a synthetic handoff document. It is validated by an offline toy ([`mission_state.py`](../../../examples/cloud-robotics/agent-mobility/mission_state.py)); there is no signature, no authenticated transport and no durable store. "MUST" and "MUST NOT" below describe what the *toy validator enforces* and what a future real implementation would have to enforce independently.

## 1. Scope

A **bundle** is the JSON document an origin executor produces at a safe checkpoint so a destination executor can continue *the same logical mission* without redoing completed steps and without creating a second live owner. It carries progress, ownership generation, freshness, replay protection, requirements the destination must satisfy, and the rollback policy. It does not carry code, process memory, model weights, sensor streams or authority to actuate (see [WHAT-IS-NOT-MOVED.md](WHAT-IS-NOT-MOVED.md)).

## 2. Document layout

All objects are **closed**: unknown or missing keys are rejected (`UNKNOWN_FIELD`, `MISSING_FIELD`). Identifiers match `^[A-Za-z][A-Za-z0-9_.:-]{0,63}$` (`BAD_IDENTIFIER` otherwise). Integers are JSON integers (booleans are not integers). Time is in **logical ticks** supplied by the caller; the toy never reads a clock.

| Path | Type | Rule |
| --- | --- | --- |
| `schema` | string | Exactly `mission-state/v1` (`UNSUPPORTED_SCHEMA_VERSION`) |
| `simulated` | boolean | MUST be `true` (`NOT_SIMULATED`). v1 documents describe simulated effects only |
| `mission.task_id` | identifier | Stable across every handoff of this mission |
| `mission.mission_revision` | integer >= 1 | Revision of the step list; a change in steps means a new revision, never an in-place edit |
| `mission.steps` | non-empty list of unique identifiers | Ordered, immutable within a revision |
| `progress.cursor` | integer >= 0 | Number of committed steps |
| `progress.completed` | list | MUST equal `steps[:cursor]` exactly |
| `progress.committed_effect_ids` | list | One effect ID per completed step; MUST equal the authoritative ledger at validation time (`STALE_CHECKPOINT`) |
| `ownership.state_owner` | identifier | The single executor that owns mission state at `epoch` |
| `ownership.epoch` | integer >= 1 | Ownership generation, see section 4 |
| `ownership.lease_expires_tick` | integer >= 0 | Informational copy of the lease; the sink holds the authoritative one |
| `handoff.handoff_id` | identifier | Human-readable label, not a security value |
| `handoff.nonce` | `[A-Za-z0-9_-]{8,64}` | Single-use replay token, section 5 |
| `handoff.sequence` | integer >= 1 | Strictly increasing per task across *committed* handoffs |
| `handoff.from_executor` / `to_executor` | identifiers | MUST differ (`SAME_EXECUTOR`); `from` MUST equal `ownership.state_owner` and `rollback.origin_executor` (`INCONSISTENT_BUNDLE`) |
| `handoff.issued_tick` / `expires_tick` | integers | `expires >= issued`; bundle valid for `issued <= now <= expires` |
| `requirements` | object | Embodiment and capability needs, see [the matrix](COMPATIBILITY-AND-CAPABILITY-MATRIX.md) |
| `rollback.on_failure` | `reissue_to_origin` or `park` | Section 7 |
| `rollback.origin_executor` | identifier | Who receives the mission back |
| `rollback.resume_from` | `effect_ledger` | Only defined value in v1 |
| `integrity.algorithm` / `digest` | `sha256` / 64 hex | Digest of the canonical JSON of the document without `integrity` (`DIGEST_MISMATCH`) |

Canonical JSON: keys sorted, separators `,` and `:`, ASCII only. The digest detects **accidental** change. Anyone who can edit the document can recompute it, so it is **not** authentication, a MAC or a signature.

A complete valid example is the generated fixture [`fixtures/bundles/valid-handoff.json`](../../../examples/cloud-robotics/agent-mobility/fixtures/bundles/valid-handoff.json) (synthetic identifiers only).

## 3. Versioning

* `schema` is an opaque, exact-match string `mission-state/vN`.
* Because objects are closed, **any** change to the set of fields, to a rule, or to the meaning of a field is a new `N`. There is no silent forward compatibility and no "ignore unknown fields".
* A destination lists the exact versions it implements (`supported_schemas`). A bundle whose version is not listed is refused with `SCHEMA_NOT_SUPPORTED`. A validator that does not implement the version at all refuses with `UNSUPPORTED_SCHEMA_VERSION`.
* v1 defines no downgrade or upgrade conversion. A converter, if ever needed, is a separate, documented, tested step that produces a new sealed bundle with a new nonce and sequence; it is out of scope here.
* `mission.mission_revision` versions the *mission*; `schema` versions the *document format*. They are independent.

## 4. Execution epoch and fencing token

* The **epoch** is the coordinator-issued ownership generation. A mission starts at epoch 1.
* The coordinator increments it on **every change of who may act**: handoff commit, rollback re-grant, and parking. It is never decremented and never reused.
* v1 uses the epoch as the **fencing token**: every effect carries the epoch under which the executor believes it acts, and the sink rejects any effect whose epoch differs from the sink's current epoch. (The idea is the standard fencing-token pattern for leases, for example as discussed by Martin Kleppmann in "How to do distributed locking", 2016, and the term number in Raft, Ongaro and Ousterhout, 2014. Those are analogies, not claims that this toy provides equivalent guarantees.) A future version may separate "ownership generation" from "token" if renewals need to be distinguished.
* The sink distinguishes `epoch < current` (`STALE_EXECUTOR`: a former owner) from `epoch > current` (`UNKNOWN_EPOCH`: a claim the sink never granted).
* Within an epoch, the executor numbers its effects `effect_seq = 0, 1, 2, ...` with no gaps. The sink rejects regressions (`EFFECT_SEQUENCE_REGRESSION`) and gaps (`EFFECT_SEQUENCE_GAP`). A new epoch restarts the counter at 0.

## 5. Replay protection

* `handoff.nonce` is **single use**. The coordinator consumes it at **commit**, together with `handoff.sequence`. A second submission of the same bundle is `REPLAYED_NONCE`.
* A bundle rejected during validation, or aborted before commit, does **not** consume its nonce or sequence; the origin builds a fresh bundle (new nonce) to retry.
* `handoff.sequence` MUST exceed the last committed sequence (`STALE_SEQUENCE`). Gaps are allowed (they arise from rejected attempts that never committed); regressions are not.
* A bundle freshly re-sealed with a new nonce but an old `ownership.epoch` is `STALE_EPOCH`; one whose `progress` lags the ledger is `STALE_CHECKPOINT`.
* Effects are deduplicated by `effect_id` for the life of the mission (`REPLAYED_EFFECT`).

## 6. State owner and capability requirements

* **State owner:** at any epoch there is zero or one owner. Zero means the mission is **parked** (fail closed). The coordinator MUST NOT issue a grant to a second executor while one is outstanding without incrementing the epoch.
* **Capability requirements** (`requirements`) describe what the destination must offer. They are *requirements on the destination*, not grants. Having the capability does not give the destination permission to act; permission is the coordinator's grant for an epoch and, in a real system, a separate actuation-authority decision that this contract does not model.

## 7. Rollback assumptions

`rollback` tells the coordinator what to do if a handoff was committed but the destination never confirms activation. The toy relies on these assumptions; a real system would have to establish each independently.

| Id | Assumption |
| --- | --- |
| R1 | Rollback is a **new grant at a higher epoch** (to the origin or to nobody). It never restores the old epoch, so a destination that did activate is fenced by the same mechanism as any stale executor. |
| R2 | The effect ledger held by the sink is the **single source of truth for progress**. After rollback the origin resumes at the ledger length, not at the bundle's `cursor` (`rollback.resume_from = effect_ledger`). |
| R3 | Effects the destination committed before rollback **stay committed**. Simulated effects are not undone; real physical effects could not be. |
| R4 | The coordinator and the sink are reliable and agree on the current grant. The toy keeps them in one Python object; a real deployment needs durable, consensus-backed state, and that is not demonstrated here. |
| R5 | Rollback to the origin requires the origin to be alive and reachable. Otherwise, or if `on_failure = park`, the mission is **parked** with no owner until a human or later protocol assigns one. |
| R6 | A lost acknowledgement is indistinguishable from a destination crash to the coordinator, so both take the same path (rollback or park). |
| R7 | The toy does not model partial network partitions between coordinator and sink, nor coordinator crashes. |

## 8. Order of checks at commit time

The validator reports the **first** failing check in this fixed order (so results are deterministic):

1. Shape and types of the document (`MALFORMED_DOCUMENT`, `MISSING_FIELD`, `UNKNOWN_FIELD`, `WRONG_TYPE`, `BAD_VALUE`, `BAD_IDENTIFIER`, `UNSUPPORTED_SCHEMA_VERSION`, `NOT_SIMULATED`, `PROGRESS_INCONSISTENT`, `INCONSISTENT_BUNDLE`)
2. Digest (`DIGEST_MISMATCH`)
3. Work remains (`MISSION_COMPLETE`)
4. Freshness (`BUNDLE_FROM_FUTURE`, `BUNDLE_EXPIRED`)
5. Parties (`SAME_EXECUTOR`, `WRONG_DESTINATION`)
6. Replay (`REPLAYED_NONCE`, `STALE_SEQUENCE`)
7. Ownership (`STALE_EPOCH`, `WRONG_STATE_OWNER`)
8. Progress against the ledger (`STALE_CHECKPOINT`)
9. Compatibility with the destination profile (first listed violation; see the matrix)

Replay is checked before the epoch so that re-submitting an already committed bundle is reported as a replay rather than as a generic stale epoch.

This order is that of `validate_for_commit`. The simulator's `submit_bundle` additionally resolves the destination executor right after the shape and digest checks (steps 1 and 2), so for a bundle with several faults at once an unknown destination (`WRONG_DESTINATION`) is reported before `MISSION_COMPLETE` or expiry; for a bundle with a single fault, and for any bundle addressed to a known destination, the two agree.

## 9. What the digest and this schema do NOT provide

No authentication of the origin, no confidentiality, no non-repudiation, no attestation of the destination, no durable atomic commit, no exactly-once execution, and no guarantee about any physical robot. Do not reuse the toy validator or sink as a safety gateway.
