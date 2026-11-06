# Stale-executor rejection and fencing rules

> **SIMULATION.** Rules enforced by an in-process toy sink ([`EffectSink`](../../../examples/cloud-robotics/agent-mobility/handoff_sim.py)). The sink shares memory with the coordinator and executors, so it is a model of an independent gate, not one. A real gate must be a separately provisioned component the executors cannot modify.

## 1. Vocabulary

| Term | Meaning |
| --- | --- |
| Current grant | The `(owner, epoch, lease)` triple the coordinator last published to the sink |
| Stale executor | An executor acting under an epoch lower than the current one, typically a former owner that missed the takeover (crashed and restarted, paused, partitioned) |
| Zombie | A stale executor that still believes it is active |
| Effect | One simulated mission-side record: `{executor, epoch, effect_seq, effect_id, step}` |

## 2. Rules (normative for the toy; each has a test)

| Rule | Statement | Reason code on violation |
| --- | --- | --- |
| F1 | An effect MUST carry the claimed epoch. A malformed effect is rejected without side effects and without raising. | `MALFORMED_EFFECT` |
| F2 | `effect.epoch < sink.epoch` is rejected **regardless of executor id, step or sequence number**. An old epoch never becomes valid again, including after a rollback to the same executor. | `STALE_EXECUTOR` |
| F3 | `effect.epoch > sink.epoch` is rejected: the sink never granted that epoch. | `UNKNOWN_EPOCH` |
| F4 | The executor MUST be the grant's owner. If the mission is parked (no owner) every effect is rejected. | `NOT_STATE_OWNER` |
| F5 | The effect MUST arrive no later than `lease_expires_tick`. Renewal is allowed only to the current owner under the current epoch, before expiry. | `LEASE_EXPIRED` |
| F6 | An `effect_id` accepted once MUST NOT be accepted again. | `REPLAYED_EFFECT` |
| F7 | Within an epoch `effect_seq` MUST be exactly the last accepted value plus one (start at 0). Lower is a regression, higher is a gap. | `EFFECT_SEQUENCE_REGRESSION`, `EFFECT_SEQUENCE_GAP` |
| F8 | `step` MUST be the next unfinished mission step per the sink's ledger. | `WRONG_NEXT_STEP` |
| F9 | A rejected effect MUST NOT change sink state. | (tested: state snapshot unchanged) |
| F10 | The sink MUST refuse to install a grant whose epoch is not above its current one. | `ValueError` (internal invariant, not a bundle reason) |
| F11 | Checks run in the order F1 to F8; the first failure is reported. | |

The order places epoch before owner so that a former owner reports the more informative `STALE_EXECUTOR` rather than a generic ownership failure, and checks `effect_id` before sequence so that a literal retransmission reports as a replay.

## 3. Handoff-side rules

| Rule | Statement | Reason code |
| --- | --- | --- |
| H1 | Commit increments the epoch and publishes the new grant to the sink **before** the destination is told to act. | (ordering in `submit_bundle`) |
| H2 | A bundle sealed under epoch `e` MUST NOT commit when the coordinator is at epoch `!= e`. | `STALE_EPOCH` |
| H3 | A committed bundle (nonce) MUST NOT commit twice. | `REPLAYED_NONCE` |
| H4 | `bundle.progress.committed_effect_ids` MUST equal the sink ledger, so a checkpoint cannot lag the truth. | `STALE_CHECKPOINT` |
| H5 | Validation failures and aborts before commit MUST leave owner, epoch, sequence and nonce set unchanged. | (tested) |
| H6 | Rollback and parking increment the epoch again (never decrement). | (tested: epochs in the trace strictly increase) |
| H7 | An origin that was told it is fenced SHOULD stop on its own (`SELF_FENCED`). This is courtesy, not security: only the sink's check protects the mission. | (not a rejection) |

## 4. Worked scenario: "old epoch resumes after takeover"

Script [`stale-executor-after-takeover`](../../../examples/cloud-robotics/agent-mobility/fixtures/scripts/stale-executor-after-takeover.json) (SYNTHETIC):

1. `cloud-01` commits `wp-01`, `wp-02` under epoch 1.
2. Handoff to `edge-01` commits; epoch becomes 2. The fence notice to `cloud-01` is **not delivered** (`deliver_fence = false`), modelling a paused or partitioned origin.
3. `cloud-01` resumes and submits `wp-03` under its belief (epoch 1): **`STALE_EXECUTOR`**. The ledger is unchanged.
4. `edge-01` submits `wp-03` under epoch 2: accepted.
5. A retransmitted `edge-01` effect: `REPLAYED_EFFECT`. Re-submitting the original bundle: `REJECTED:REPLAYED_NONCE`. A stale `cloud-01` lease renewal: `STALE_EXECUTOR`.

The mission ends with a gap-free ledger `wp-01..wp-03` and no duplicate effect.

## 5. Residual risks the toy does not remove

| Risk | Why it remains |
| --- | --- |
| Effect already emitted by a zombie *before* the sink saw the new epoch | A real actuator may have moved; a sink cannot recall it. Needs leases short enough, safe-stop and independent actuator-side checks |
| Sink or coordinator crash or split brain | Single in-memory object here; real fencing needs durable, linearizable grant state |
| Executor that ignores the fence and talks to hardware directly | Fencing only works if the *only* path to effects is the gate |
| Forged effects | `executor` is a label; there is no authentication |
| Clock skew | Leases use caller-supplied logical ticks; real clocks need a documented bound |
| Lost acknowledgement of an *effect* | The executor cannot tell "rejected" from "accepted but unacknowledged"; it must reconcile against the ledger. The toy models retransmission (`REPLAYED_EFFECT`) but not an executor-side reconcile protocol |
