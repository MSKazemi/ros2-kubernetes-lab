# e02: DDS resilience under impairment (offline harness)

Addresses issues #48 (DDS vs Zenoh under impairment) and #18 (DDS/monitoring benchmark suite).

This directory contains the **measurement and analysis side** of a resilience experiment, built to run entirely offline on **deterministic synthetic traces**. It defines the scenario matrix, a trace analyzer, and fixtures that exercise the analyzer. **No live experiment has been run.**

## What this does NOT claim

- **No measured results.** Nothing here reports how Fast DDS, Cyclone DDS, Zenoh or any ROS 2 setup behaves. The numbers you can print from `fixtures/` describe the *generator's assumptions*, not a middleware.
- **No cross-node or cross-cluster validation.** Nothing was run in Kubernetes, kind, Docker or on a network. The live recipes in `matrix/matrix.yaml` are documentation, flagged **NOT RUN**, and this code never executes them.
- **No DDS-vs-Zenoh comparison yet.** The matrix lists the RMWs to repeat each cell with (`rmw_for_live_runs`), but no run exists for any of them.
- **Hypotheses are not findings.** Each cell's `hypothesis` is a statement for a future live run to confirm or refute.
- **Synthetic checks are pipeline sanity checks.** `synthetic_checks` verify that the analyzer reads a fixture as its generator intended. They are circular with respect to real behaviour on purpose and prove nothing about it.
- Latency percentiles with fewer than 100 samples have an unresolved p99 (it equals the maximum); the output says so.

## Layout

| Path | Purpose |
|---|---|
| `matrix/matrix.yaml` | 2 reliability x 6 impairment cells, workload, parameters, hypotheses, live-run recipe (NOT RUN), synthetic-model assumptions |
| `ddsres/trace.py` | Native trace format `rrl.trace/1`, strict validation, optional flat-JSONL `Adapter` |
| `ddsres/seqprobe.py` | Reader for the `examples/ros2-sequence-probe` schema-v1 event log |
| `ddsres/metrics.py` | The metrics (definitions below) |
| `ddsres/synth.py` | Seeded SYNTHETIC fixture generator |
| `ddsres/checks.py` | Evaluates a cell's `synthetic_checks` |
| `fixtures/` | 12 generated traces plus `MANIFEST.json` (sha256); every file is labelled SYNTHETIC |
| `tests/test_e02.py` | unittest tests, including negative cases |
| `run.py` | Entry point (`python3 experiments/e02-dds-resilience/run.py --help`) |

Dependencies: Python 3 standard library plus PyYAML (matrix loading only). No network, no cluster, no root.

## Usage (from the repository root)

```sh
R=experiments/e02-dds-resilience
python3 $R/run.py validate-matrix          # matrix covers the full cross product, recipe flagged NOT RUN
python3 $R/run.py recipe reliable__loss    # print the documented (not executed) live recipe
python3 $R/run.py generate                 # rewrite fixtures/ (byte-identical for the same seeds)
python3 $R/run.py check-fixtures           # analyze all fixtures, run synthetic_checks
python3 $R/run.py analyze $R/fixtures/best_effort__partition.synthetic.jsonl
# one real run of the sequence probe (publisher + subscriber logs, one file or two):
python3 $R/run.py analyze-seqprobe pub.jsonl sub.jsonl [--markers markers.jsonl]
python3 -m unittest discover -s $R/tests -t $R   # tests
```

`analyze` and `analyze-seqprobe` exit 2 with a one-line error on any invalid input; they never guess.

## Metrics (computed only from the records supplied)

| Metric | Definition |
|---|---|
| `delivery_completeness` | distinct sent seqs received at least once / distinct sent seqs |
| `loss_ratio` | 1 - completeness |
| `duplicate_copies`, `duplicate_ratio` | received records beyond the first per seq; `duplicate_ratio` = copies / *solicited received records* (received records whose seq was sent, i.e. `received_total - unsolicited`; reported as `counts.solicited_received`); null if that is 0 |
| `reorder` | RFC 4737 *NextExp* over first deliveries in arrival order; a delivery with `seq < NextExp` is reordered. Gaps from loss are not reordering |
| `latency` p50/p95/p99 | first receive minus send, same clock domain only. **Nearest rank**: sorted samples, 1-based rank `ceil(p/100 * n)`, an actual sample, no interpolation. `n < 2` is an error in `nearest_rank`; `analyze` reports `latency: null` with a reason (or raises with `require_latency=True`) |
| `fault_windows` | `<name>_begin` / `<name>_end` markers paired in order. `delivery_gap_ns` = first receive after begin minus last receive at or before begin. `recovery_time_ns` = first receive at or after end minus end; null without an end marker, `recovered: false` if nothing arrived. A buffered stale message arriving after end counts as resumed delivery |
| `resources` | min/mean/max of `cpu_pct` and `mem_bytes` from `resource` records; **null when absent** |

Null means "not in the input"; nothing is defaulted or estimated.

### Validation behaviour

| Input defect | Result |
|---|---|
| empty file, or no send records | `EmptyTraceError` |
| truncated (no footer / count mismatch / cut last line / no probe `stop` event) | `TruncatedTraceError` |
| timestamps going backwards within one stream | `NonMonotonicClockError` |
| send/recv/marker in different clock domains | `ClockDomainError` (or latency and fault times null with `--mixed-clock null`) |
| receive earlier than send in one domain (negative latency) | **not an error**: latency percentiles are `null`, `latency_unavailable_reason: negative_latency_samples`, `latency_diagnostics` = `{total_samples, negative_samples, min_ns}`, plus a warning; loss, duplicate, reorder and fault-window metrics are still produced and the command exits 0. `wall`/`ros` clocks on two nodes can legitimately skew. (`require_latency=True` raises instead.) |
| duplicate send seq (native, or in probe logs: log passed twice / runs concatenated; message names both positions), unknown fields/schema, bad types, non-integer timestamps | `TraceError` |

## Trace formats

**Native `rrl.trace/1`** (used by fixtures): header line (`type: header`, `schema`, `synthetic`, `label`, optional `default_clock`), then `send` / `recv` (`seq`, `t_ns`, `clock`), `marker` (`name`, `t_ns`, `clock`), optional `resource` (`t_ns`, `node`, `cpu_pct`, `mem_bytes`), then `{"type":"footer","records":N}`.

**Sequence probe (schema_version 1)**: read directly from `examples/ros2-sequence-probe` logs. `send` and `recv` events map straight across. `wall` and `ros` clocks are single domains; `monotonic` becomes `monotonic@<node>` because monotonic origins differ per node, so a publisher/subscriber pair on two nodes using `monotonic` is a mixed-domain trace and latency is refused. Wall-clock latency across nodes carries a warning because clock synchronisation is not measured. The probe has no fault markers; supply them with `--markers` (`{"name":"restart_begin","t_ns":...,"clock":"wall"}` per line). A test (`test_contract_with_real_seqprobe_writer`) feeds the probe's own simulator output through this reader and is skipped when the probe directory is absent.

## Synthetic fixtures

`python3 run.py generate` writes `fixtures/<reliability>__<impairment>.synthetic.jsonl` from fixed per-cell seeds (`matrix.yaml`). The header carries `"synthetic": true` and a `label` starting with `SYNTHETIC`; a test checks the committed files match the generator byte for byte. The generator's models (retransmit timing, in-order delivery for reliable, partition catch-up with `keep_last` depth, rediscovery delay) are **assumptions** written in `synthetic_model`, chosen to produce loss, duplicate, reorder and outage-gap shapes for the analyzer.

## Running it live later (not done here)

`matrix/matrix.yaml` -> `live_recipe_common` and `live_recipe` describe the steps and `tc netem` commands. They require an explicit safe local context: a throwaway kind cluster created for this purpose, `NET_ADMIN` granted deliberately to the subscriber pod, never the host network namespace and never a shared cluster. Record the pod-to-node mapping, ROS distribution, RMW and discovery mode (see `docs/ROS2-KUBERNETES-DDS-GUIDE.md`), and keep the raw logs next to any report. Only observed output from such runs may be reported as a result.
