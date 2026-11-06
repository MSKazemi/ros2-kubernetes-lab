# Model-serving fairness simulation

A deterministic, CPU-only, standard-library-only **discrete-event simulation** of a shared
model-serving node used by several robots. It asks a narrow question: *when one client floods
the node, how do different queue disciplines and model-cache placement change deadline misses,
tail latency and per-client fairness?*

Everything this experiment prints is **SIMULATED**. See [Limitations](#limitations) before
quoting any number. Related issues: #107 (fair model serving and model-cache placement under
fleet contention), #69, and the fair multi-robot scheduling scenario #87.

## Quick start

From the repository root (tested with Python 3.12; standard library only, no network, no GPU):

```sh
# Markdown table for the default scenario, three seeds, all schedulers x placements
python3 experiments/model-serving-fairness/run_simulation.py

# JSON + Markdown files, with worker 0 down from t=30 s to t=50 s
python3 experiments/model-serving-fairness/run_simulation.py --seeds 1,2,3 \
    --worker-down 0:30:50 --json-out serving.json --markdown-out serving.md

# A scenario that stresses cache placement instead of queue discipline
python3 experiments/model-serving-fairness/run_simulation.py \
    --config experiments/model-serving-fairness/data/cache_pressure.json --schedulers fifo

# Tests (about one second)
python3 -m unittest discover -s experiments/model-serving-fairness/tests \
    -t experiments/model-serving-fairness
```

Runner exit codes: `0` success, `2` invalid input or configuration (message on stderr).
Output is byte-identical for the same arguments; there are no timestamps and no host data.

## Model

* **Clients** (simulated robots) each have an arrival process, a model mix, a relative
  deadline and a DRR weight. Arrival kinds: `fixed` (explicit times, used in tests),
  `periodic` (period, offset, optional jitter), `poisson` (rate, optional start/end), and
  `bursty` (a burst of N requests every interval, spaced `burst_gap` apart). A client with
  `"noisy": true` is a label used only for the *quiet-client* aggregate below.
* **Workers**: `workers` identical workers, one request at a time each, each with its **own**
  model cache of `cache_capacity` size units. A request occupies a worker for its sampled
  service time, plus the model's `load_cost` when the model is not resident (cache miss).
  The cache is updated at dispatch. Service time is `mean * (1 + jitter * (2u - 1))` with
  `u ~ U(0,1)`, sampled once per request at generation, so every scheduler sees the same
  workload for a given seed.
* **Schedulers** (`--schedulers`):
  * `fifo` - by (arrival time, request id).
  * `edf` - earliest absolute deadline first, ties by arrival then id.
  * `drr` - **Deficit Round Robin** over per-client queues (Shreedhar and Varghese, 1995).
    Cost of a request = its sampled warm service seconds (model load is not charged). Each
    visit adds `drr_quantum * client.weight` seconds of deficit; a client is served while its
    head request fits in its deficit; a client whose queue empties leaves the ring and its
    deficit resets to 0. This is DRR, not weighted fair queuing (no virtual finish times).
* **Cache**: per-worker, size-aware **LRU** eviction (hit moves to most-recent; a miss evicts
  least-recent models until the new one fits). A worker failure clears that worker's cache.
* **Placement** (`--placements`): after the scheduler picks a request, `first_idle` gives it
  the lowest-numbered idle worker; `cache_aware` prefers an idle worker that already holds the
  model, then an idle worker with enough free cache (no eviction), then the lowest-numbered
  idle worker. Placement never reorders the queue, so it cannot change fairness by itself; it
  only matters when two or more workers are idle at once.
* **Failure injection**: `failures: [{worker, start, end}]` in the config or repeatable
  `--worker-down W:START:END`. At `start` the worker's in-flight request is aborted and
  re-queued with its original arrival time and deadline (counted in
  `retried_after_worker_failure`), and its cache is cleared; the worker is unusable until `end`.
  Windows on one worker may be back-to-back (`[10,20]` then `[20,30]` keeps the worker down
  across t=20) but may not overlap; windows on different workers may overlap. Availability is
  tracked as an outage counter, so event order at an equal timestamp cannot bring a worker up
  early. At an equal timestamp a completion finishes normally before a window opens, an arrival
  at a window's start cannot use that worker, and an arrival at its end can.
* **Overload controls**: `queue_capacity` rejects arrivals when that many requests are already
  waiting (`rejected`); `drop_expired` discards a request at dispatch if its deadline has
  already passed (`dropped`). Both are off by default. `drain: false` stops at `duration`
  and reports `unfinished`.
* **Event order** at equal timestamps: completion, worker-down, worker-up, arrival; the
  dispatcher runs after every event. Randomness comes from `random.Random` streams seeded by
  `"<seed>|<client id>|<stream>"`, independent of `PYTHONHASHSEED`.

## Metrics (all SIMULATED)

| Field | Definition |
|---|---|
| `latency_s.p50/p95/p99` | **Nearest-rank** percentile of finish - arrival (queueing + load + service) over completed requests: `rank = ceil(p*n/100)` in integer arithmetic, value = `sorted[rank-1]`. `null` if none completed. |
| `deadline_miss_rate` | (late completions + dropped + unfinished past deadline) / admitted, where admitted = arrivals - rejected. |
| `goodput_rate` | on-time completions / all arrivals (rejections count against the system). |
| `quiet_clients_deadline_miss_rate` | Same miss definition over clients not marked `noisy`. |
| `jain_goodput_index` | Jain's index over per-client `on_time / arrivals`: `(sum x)^2 / (n * sum x^2)`; 1.0 = even, 1/n = one client gets everything. If every client is 0 the value is defined as 1.0 (equally starved), so read it with `goodput_rate`. |
| `clients[id].max_queue_wait_s`, `starved_requests` | Wait = first start - arrival (or time to drop / end of run if never started). Starved = wait > `starvation_wait` seconds. |
| `clients_with_no_service` | Clients with arrivals but zero completions. |
| `cache.hit_rate` | hits / (hits + misses), counted per dispatch. |
| `totals.rejected`, `totals.dropped` | Admission rejections and expired drops. |
| `worker_busy_fraction` | Worker busy seconds / (workers * run length). |

The JSON report has top-level keys `label`, `schema_version`, `disclaimer`, `scenario`,
`seeds`, `schedulers`, `placements`, `config` (echo of the input), and `runs`. Each element of
`runs` is one (seed, scheduler, placement) result containing `label: "SIMULATED"`, `seed`,
`scheduler`, `placement`, `worker_failures`, `end_time_s`, `totals`, `deadline_miss_rate`,
`goodput_rate`, `quiet_clients_deadline_miss_rate`, `latency_s`, `jain_goodput_index`,
`starved_requests`, `clients_with_no_service`, `cache`, `worker_busy_fraction`, and a `clients`
object keyed by client id. The field set is pinned by `tests/test_runner.py`.

## Scenarios

* `data/default_fleet.json` - six clients (three periodic, two Poisson, one bursty
  noisy neighbour) on two workers whose caches hold every model. Illustrates queue discipline.
* `data/cache_pressure.json` - five clients, four models, three workers with two cache slots
  each. Illustrates why placement matters when the cache is smaller than the model set.

All parameters in these files are **assumed**, not measured. Copy a file and edit it to try
other settings; unknown keys and invalid values are rejected with a clear error.

## Tests

`tests/` uses `unittest`. It covers: determinism per seed and identical workload across
schedulers; hand-computed request orders for FIFO, EDF, and DRR (equal weights, weight 2,
cost-aware); LRU and size-aware eviction and cache-aware placement; nearest-rank percentiles and
Jain index known values; overload (queue rejection, expired drops, no-drain); worker failure
(restart, cache clear, takeover, all workers down, stale completion); starvation and
no-service accounting; request-conservation invariants; invalid configuration and runner
errors.

## Limitations

* **No GPU and no real model.** Nothing here runs, loads, or times any model. There is no
  GPU memory, batching, concurrency within a worker, preemption, or interconnect model.
* **Service times, load costs, cache sizes, deadlines and arrival rates are assumed
  parameters** chosen for illustration. They are not measurements of any real system.
* **Results are illustrations, not benchmarks.** Do not quote a miss rate or percentile from
  this simulation as a property of a real deployment. Conclusions hold only for the stated
  model and seeds; with different parameters the ranking of schedulers can change.
* Single node only: no network, DDS, or Kubernetes behaviour is modelled, and nothing here
  shows cross-node delivery. Requests are independent (no pipelines or retries by clients).
* Simplifications: cache state changes at dispatch; one request per worker; failures are
  fail-stop with immediate restart-from-scratch on recovery; DRR cost ignores model load time.
* A handful of seeds and a 120 s horizon give no confidence intervals.
