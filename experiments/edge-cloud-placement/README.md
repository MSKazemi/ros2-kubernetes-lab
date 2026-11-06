# Edge/cloud inference placement: a deterministic SIMULATION

**SIMULATION ONLY.** Every number this experiment prints is a **SIMULATED model output** computed from the parameters in a JSON config and a fixed seed. It is **not** a measurement of a robot, a network, a ROS 2 / DDS stack, a Kubernetes cluster, a GPU or any cloud service, and nothing is ever sent to an actuator. The default parameters are illustrative placeholders, not data from any real system.

Related issues: #85 (network-aware inference placement matrix, scenario S2) and #62 (action freshness, edge versus cloud).

## What question it explores

For a stream of perception-to-action requests, each with its own deadline, when should inference run on the robot (LOCAL) and when on a remote server (REMOTE), given that the network has jitter, loss and outage windows and the remote may be unable or unwilling to serve? And what must the consumer do with answers that arrive late, twice, for the wrong request or from a source that was not allowed?

The simulator compares four placement policies on **identical random draws** (common random numbers), so differences come from the policy rather than from luck.

| Policy | Behaviour |
| --- | --- |
| `always_local` | Every request runs on the local worker. |
| `always_remote` | Every request is sent to the remote. No eligibility check, no fallback. |
| `deadline_aware` | Remote only if `predicted round trip + margin <= request budget` **and** the remote is eligible as far as the policy knows. Otherwise local. Single path, no fallback after sending. A probe is allowed every `probe_interval_ms` so recovery after an outage is noticed. |
| `hedged_fallback` | Same routing as `deadline_aware`, plus a local fallback launched when the remote answers with an explicit reject, or when a hedge timer fires with no answer. |

## Run it

Standard library only (written for Python 3.10+; run only on 3.12.3 so far). No network, no ROS, no Docker, no GPU.

```sh
# from the repository root
python3 experiments/edge-cloud-placement/placement_sim.py \
  --config experiments/edge-cloud-placement/configs/default.json

# JSON report plus one decision log per policy
python3 experiments/edge-cloud-placement/placement_sim.py \
  --config experiments/edge-cloud-placement/configs/default.json \
  --out /tmp/placement-summary.json --log-dir /tmp/placement-logs

# tests (standard library unittest)
python3 -m unittest discover -s experiments/edge-cloud-placement/tests \
  -t experiments/edge-cloud-placement
```

Same config and seed give byte-identical output. An invalid config exits with status 2 and a message on stderr. `reports/default.summary.json` and `reports/default.table.txt` are the committed output of the default config; regenerate them with the first command plus `--out`.

## Model

Time is integer logical milliseconds. Request `i` is captured at `i * interval_ms` and has an absolute deadline `capture + budget`. A response arriving **exactly at** the deadline is on time.

* **Local**: a single FIFO worker; compute time `compute_base_ms + U[0, compute_jitter_ms]`. Local is eligible if `memory_mb >= model_memory_mb`; otherwise a request routed local has no viable executor.
* **Remote**: unlimited parallelism (a stated simplification). Eligible only if its free memory *at the moment the request arrives* is at least `model_memory_mb` (`memory_mb` constant, or a `memory_schedule` step function). Otherwise it answers with an explicit reject `ineligible_memory`. It may also reject at random (`overloaded`, `reject_probability`).
* **Capability advertisement**: policies learn remote eligibility with a lag (`advert_lag_ms`), so a policy can still send to a remote that just became ineligible and receive a reject.
* **Network**: one-way delay `one_way_base_ms + U[0, one_way_jitter_ms]` each direction; independent loss per direction; **outage windows** during which anything *sent* is dropped (messages already in flight are still delivered, a simplification); a **recovery** period after each outage in which one-way delay is multiplied by `recovery_delay_factor`; duplicated deliveries of a response; spurious responses carrying IDs that were never issued.
* **Predictor** (`deadline_aware`, `hedged_fallback`): an EWMA of *observed* round trips, updated only when a response has actually arrived. A timeout is a censored observation and raises the estimate to at least the missed budget. Nothing about the future is used.
* **Hedge** (`hedged_fallback`): fires at `capture + hedge.delay_ms` (default: predicted RTT plus margin at launch time), never later than the last moment a worst-case local run could still meet the deadline. It is skipped if the request is already applied or a local run cannot possibly finish in time.

### The non-actuating sink (SIMULATION)

The sink has no output channel. It records one decision per action-bearing response, always with `"actuated": false` and `"label": "SIMULATION"`:

* `would_apply`, or
* `rejected` with exactly one reason, checked in this order:

| Order | Reason | Meaning |
| --- | --- | --- |
| 1 | `unknown_request_id` | The ID was never issued. |
| 2 | `duplicate_response_id` | The same response was delivered again, or the request was already applied by another path. |
| 3 | `ineligible_source` | The request is `local_only` but the response came from the remote. |
| 4 | `late_after_deadline` | Arrived after the absolute deadline. |
| 5 | `superseded_request` | A newer request was already applied. |

A rejected response does not block a later valid one for the same request. Explicit remote rejects are not sink decisions; they are logged as `remote_reject` events and counted in `remote_rejects`.

## Config schema (`schema_version` 1)

Unknown keys are rejected, as are non-finite numbers, booleans where a number is expected, probabilities outside [0, 1] and overlapping outages. All durations are integer milliseconds.

| Key | Type / constraint | Notes |
| --- | --- | --- |
| `schema_version` | `1` | |
| `seed` | integer | |
| `description` | string, optional | |
| `stream.num_requests` | int, 1..200000 | |
| `stream.interval_ms` | int > 0 | |
| `stream.deadline_ms` | int > 0, or `{min, max}` with `0 < min <= max` | Per-request budget; drawn uniformly from the range. |
| `stream.local_only_probability` | [0, 1], default 0 | Requests that must not be served remotely. |
| `local.memory_mb`, `local.model_memory_mb` | int >= 0 | |
| `local.compute_base_ms`, `local.compute_jitter_ms` | int >= 0 | jitter default 0 |
| `remote.model_memory_mb` | int >= 0 | |
| `remote.memory_mb` **or** `remote.memory_schedule` | int, or list of `{from_ms, memory_mb}` starting at 0, strictly increasing | Exactly one of the two. |
| `remote.compute_base_ms`, `remote.compute_jitter_ms` | int >= 0 | |
| `remote.reject_probability` | [0, 1], default 0 | |
| `remote.advert_lag_ms` | int >= 0, default 0 | |
| `network.one_way_base_ms`, `network.one_way_jitter_ms` | int >= 0 | |
| `network.loss_probability` | [0, 1] | per direction |
| `network.duplicate_probability`, `network.duplicate_extra_delay_max_ms` | [0, 1]; int >= 1 (default 50) | |
| `network.spurious_response_probability` | [0, 1] | |
| `network.outages` | list of `{start_ms, end_ms}`, `end > start`, non-overlapping | start inclusive, end exclusive |
| `network.recovery_ms`, `network.recovery_delay_factor` | int >= 0; number >= 1 | |
| `predictor.prior_rtt_ms`, `.alpha`, `.margin_ms`, `.probe_interval_ms` | number >= 0; (0, 1]; number >= 0; int > 0 | optional section |
| `hedge.delay_ms` | int >= 0 or `null` | `null` = predicted RTT + margin |
| `policies` | non-empty subset of the four policy names | default: all four |

## Output fields

The report (`--out`, or `--json`) has `label` (`"SIMULATION"`), `banner`, `simulation: true`, `measured: false`, `schema_version`, `seed`, `config_sha256`, `description` and `policies.<name>` with:

| Field | Meaning |
| --- | --- |
| `requests_total`, `on_time_applied`, `on_time_rate` | Requests whose action the sink would have applied by the deadline. |
| `deadline_miss`, `deadline_miss_causes` | Requests with no would-apply, by first matching cause: `no_viable_executor`, `ineligible_source`, `remote_rejected`, `late_response`, `superseded_response`, `no_response`. |
| `stale_rejected` | Sink rejections for `late_after_deadline` plus `superseded_request`. |
| `rejected_by_reason`, `sink_decisions_total` | All five sink reasons, zero-filled. |
| `fallback_count` | Requests whose applied action came from a hedge/fallback local run. |
| `fallback_launched` | Fallback local runs started (the cost side of the hedge). |
| `routed_local`, `routed_remote` | Initial routing decision per request. |
| `applied_by_source` | `{local, remote}` counts of applied actions. |
| `remote_timeouts`, `remote_rejects` | Remote attempts with no answer by the deadline; explicit rejects by reason. |
| `simulated_latency_ms` | `mean, p50, p95, max` of capture-to-apply logical time for applied actions (`null` if none). Nearest-rank percentiles. |
| `by_capture_time` | On-time counts for requests captured during an outage or recovery window versus otherwise. |
| `actuated` | Always `false`. |

`--log-dir` writes `<policy>.decisions.jsonl` with `route`, `local_launch`, `remote_request_lost`, `remote_reply_lost`, `remote_timeout`, `remote_reject`, `no_viable_executor` and `sink` records.

## Example output (SIMULATED, default config, seed 20261106)

```
policy               on_time_rate  on_time_applied    deadline_miss   stale_rejected   fallback_count    routed_remote
always_local               0.9167              275               25               25                0                0
always_remote              0.7000              210               90                9                0              300
deadline_aware             0.8567              257               43               16                0              200
hedged_fallback            0.9333              280               20               20               29              200
```

These values only describe the toy model under the placeholder parameters in `configs/default.json`. They support no claim about real robots, networks or clouds. What the run does illustrate mechanically: the hedge buys on-time rate at the price of many extra local runs (`fallback_launched` is 135 for 29 rescued requests in this config), and `deadline_aware` without a fallback can do worse than `always_local` when the remote path fails after the decision is made. Different parameters can reverse these orderings; change the config and look.

## Limitations

* A logical-time toy model, not a packet-level network emulator, DDS/QoS model, model-serving queue or scheduler.
* Remote capacity is unlimited and its compute time does not depend on load; local is one FIFO worker. There is no accuracy difference between local and remote model outputs.
* Messages in flight when an outage starts are still delivered. Loss and jitter are i.i.d. per message (no burst loss model).
* "Memory" eligibility is a single scalar threshold; there is no GPU, bandwidth, payload-size or energy model.
* Clocks are perfect and shared; real systems need clock-offset handling for freshness checks.
* Default parameters are illustrative. `superseded_request` is covered by a sink-level unit test but does not occur in the default scenario.
* The predictor is one simple EWMA with a probe timer; other estimators or breakers may behave quite differently.
* The sink only records. Nothing here validates a safe-stop strategy or any safety property of a real controller.

## What a real measurement would need (NOT RUN)

None of the following has been done; this directory contains no measured data.

1. A real ROS 2 baseline (Jazzy image, kind or other cluster) with an observed publish-to-receive path, from the repository's existing ROS 2 test scaffolding.
2. A real inference service at the edge and in the cloud, with the same model, versions pinned and recorded.
3. Controlled network impairment on an isolated test network (not the host network), with the impairment profile recorded and independently verified.
4. Clock synchronisation (for example PTP or NTP with a measured offset bound) so one-way age and freshness can be computed, or round-trip-only measurement.
5. Time-stamped request/response traces from both ends, repeated runs, and confidence intervals before any comparison.
6. A mapping from the simulator's config fields to measured quantities (which would then replace the placeholder parameters).
7. Review of any safety or actuation path by the owners of the robot; this experiment must never be attached to an actuator.

## Provenance

The design was informed by an earlier, unpublished preflight experiment on simulated action freshness. Ideas carried over conceptually: logical-time event ordering with a response at exactly the deadline counting as on time; timeout events per request; an inert, non-actuating decision record in place of any control output; and reporting rejections with reasons. This implementation is independent: a different event model (discrete-event queue with network, outage, recovery, eligibility and duplicate semantics), a predictor-driven placement gate, hedging, and a five-reason ordered sink. No text or code was copied.

## Files

* `placement_sim.py`: simulator, config validation and CLI.
* `configs/default.json`: illustrative configuration.
* `tests/test_placement_sim.py`: unit tests (valid and negative paths).
* `reports/default.summary.json`, `reports/default.table.txt`: committed output of the default config (SIMULATED).
