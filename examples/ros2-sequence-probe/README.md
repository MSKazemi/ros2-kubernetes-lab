# ROS 2 sequence probe

A small probe that answers one question about a ROS 2 topic: **which numbered messages that were
sent arrived, and did any arrive twice or out of order?** It is a counting tool for the lab's
educational experiments (see issue #52 for the `ros2_pulse` telemetry pilot context). It is not a
benchmark and not a robot control component.

| Part | Needs ROS? | Status in this change |
|---|---|---|
| `seqprobe/` core: message plan, payload format, JSON-lines events, sequence tracker, timeouts, offline analysis, synthetic fault simulation | No (Python standard library) | Unit-tested, see "Tests" |
| `rclpy_adapters/publisher_node.py`, `subscriber_node.py` | Yes (`rclpy`, `std_msgs`; imported lazily) | **NOT RUN.** Written without a ROS installation; only checked to import without ROS and to reject bad arguments |
| Running the adapters in the Jazzy image or a kind cluster | Yes | **NOT RUN.** Commands below are documentation only |

No Kubernetes manifest is included: the Jazzy image does not contain this code, so a pod would need
either an image rebuild or the files mounted from a ConfigMap. That decision is left to the
maintainers.

## What it does

* **Publisher:** sends `count` messages with sequence IDs `0..count-1` at `rate_hz`, each carrying
  an ASCII payload of exactly `payload_bytes` bytes (deterministic padding from `--seed`). It logs
  `start`, one `send` per message, and `stop`.
* **Subscriber:** decodes each payload, logs a `recv` event, and feeds a tracker that counts gaps,
  duplicates and reordering. It stops on completion or on a timeout and logs `stop` with the verdict.
* **Offline:** `python3 -m seqprobe analyze <log>` recomputes the same verdict from a log file.

## Log schema (version 1)

JSON Lines: one object per line, keys always in the order below, no unknown keys, no duplicate keys, no `NaN`.
The parser (`seqprobe/events.py`) is strict and reports the line number of the first bad record.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Always `1` |
| `event` | string | `start`, `send`, `recv`, `timeout`, `stop` |
| `role` | string | `publisher` (events `start`, `send`, `stop`) or `subscriber` (`start`, `recv`, `timeout`, `stop`) |
| `run_id` | string | Exactly `[A-Za-z0-9_-]{1,32}` (full match: a trailing newline, space or non-ASCII lookalike is rejected); must match on both sides, other runs are counted and ignored |
| `node` | string | Node name: printable ASCII (0x21-0x7e), so no whitespace, control or non-ASCII characters |
| `topic` | string | Topic name: same character rule as `node` |
| `seq` | int or null | Sequence ID (>= 0). Non-null exactly for `send` and `recv` |
| `payload_bytes` | int or null | Payload size in bytes. Non-null exactly for `send` and `recv` |
| `ts_ns` | int | Time of the event in nanoseconds, **on the clock named in `clock`** |
| `clock` | string | `monotonic`, `wall` or `ros` (next section) |
| `sent_ts_ns` | int or null | `recv` only: the sender's timestamp, copied out of the payload |
| `sent_clock` | string or null | `recv` only: the clock `sent_ts_ns` was taken on |
| `detail` | object or null | `start`: config, `expected_count`, clock description, `synthetic` flag, QoS. `timeout`: `reason` (`first_message`, `idle`, `overall`). `stop`: publisher `{sent, reason}`, subscriber `{verdict, malformed, foreign_run}` |

Example `recv` line:

```json
{"schema_version":1,"event":"recv","role":"subscriber","run_id":"r1","node":"sub","topic":"/seqprobe","seq":3,"payload_bytes":64,"ts_ns":1700000000300000000,"clock":"wall","sent_ts_ns":1700000000299000000,"sent_clock":"wall","detail":null}
```

Payload wire format (`std_msgs/String`, or `ByteMultiArray` carrying the same ASCII bytes):
`SQP1;<run_id>;<seq, 10 digits>;<sent_ts_ns, 20 digits>;<sent_clock>;<padding, lowercase hex, may be empty>`.
Digits are ASCII `0-9` only; every field is matched in full, so any other character is rejected.

## Clock semantics

Every timestamp is stored next to the name of its clock. Clocks are never converted or mixed.

| `clock` | Source | Comparable across nodes? |
|---|---|---|
| `monotonic` | `time.monotonic_ns()` | **No.** Arbitrary origin, valid only within one node |
| `wall` | `time.time_ns()` (Unix epoch, UTC) | Only up to the nodes' clock-synchronisation error, which this tool does **not** measure |
| `ros` | `node.get_clock().now()` | System time, or simulated time if `use_sim_time` is set. Adapters only |

Rules the code enforces (all covered by tests):

* A `(run_id, role, node, topic)` stream may not change `clock` part-way through a log
  (`ClockMismatchError`).
* `Event.elapsed_since()` raises `ClockMismatchError` for different clocks, and for `monotonic`
  readings from different nodes.
* Timeouts always use the local monotonic clock, whatever clock is logged, so a wall-clock step
  cannot trigger or hide a timeout.
* `send` timestamps are read immediately before the publish call, `recv` timestamps at the start of
  the callback. The tool never subtracts the two to report a latency.

## Verdict

Per subscriber stream: `expected_count`, `received_total`, `unique`, `duplicates`, `reordered`
(a never-seen sequence ID arriving after a higher one), `gap_events`, `unexpected` (outside
`0..expected_count-1`), `missing` and `missing_ranges`, `completion`, `ok`, `tail_loss_detectable`.

* `completion`: `complete` (every ID received), `timeout`, `incomplete` (stopped early without a
  timeout), `unknown` (no expected count and no timeout).
* `ok` is true only for `complete` with no duplicate, reordered, unexpected or missing message.
* Without an expected count, messages lost at the **end** of the run cannot be seen. The verdict says
  so (`tail_loss_detectable: false`) and is never `ok`. Pass `--expected-count`.

## Tests

Standard library only; no ROS, network or cluster. From the repository root:

```sh
python3 -m unittest discover -s examples/ros2-sequence-probe/tests -t examples/ros2-sequence-probe
```

Covered: deterministic plan and payloads, gap, head/tail loss, duplicate, out-of-order, first-message
/ idle / overall timeout, zero or negative count, bad rate and payload size, malformed payloads and
log lines (with line numbers), clock-semantics mismatch, adapters importing without `rclpy` and
rejecting bad arguments with exit code 2, and CLI exit codes. These tests exercise the counting
logic over an in-memory channel. They do **not** test DDS, a network, or Kubernetes.

Without ROS you can also generate and analyse **SYNTHETIC** logs (generated timestamps, fixed fake
delay, `detail.synthetic = true`; nothing is measured):

```sh
cd examples/ros2-sequence-probe
python3 -m seqprobe simulate --count 20 --drop 5,6 --duplicate 9 --swap 12 --out /tmp/demo.jsonl
python3 -m seqprobe analyze /tmp/demo.jsonl    # exit 0 ok, 1 not ok, 2 bad input
python3 -m seqprobe plan --count 5 --rate-hz 2 # the deterministic send schedule
```

## Running the adapters in the Jazzy container (documented, NOT EXECUTED)

These commands were not run. They assume the image from `ROS2/Dockerfile` (the Makefile's
`make demo` tags it `ros2k8s-demo-ros:local`) and exercise **one container with two processes**, the
same scope as `scripts/test-ros2-image.sh`. A pass would say nothing about cross-container,
cross-node or Kubernetes DDS delivery.

```sh
docker run --rm -v "$PWD/examples/ros2-sequence-probe:/probe:ro" ros2k8s-demo-ros:local bash -c '
  source /opt/ros/jazzy/setup.bash
  export ROS_DOMAIN_ID=42 PYTHONDONTWRITEBYTECODE=1
  python3 /probe/rclpy_adapters/subscriber_node.py --run-id r1 --expected-count 20 \
      --reliability reliable --depth 10 --log-file /tmp/sub.jsonl &
  sub=$!
  python3 /probe/rclpy_adapters/publisher_node.py --run-id r1 --count 20 --rate-hz 5 \
      --payload-bytes 64 --reliability reliable --depth 10 --log-file /tmp/pub.jsonl
  wait "$sub"; rc=$?
  cat /tmp/sub.jsonl; exit "$rc"'
```

Adapter flags: `--run-id` (required), `--topic`, `--node-name`, `--msg-type string|bytes`,
`--clock monotonic|wall|ros`, `--reliability reliable|best-effort`, `--durability
volatile|transient-local`, `--depth N`, `--log-file PATH|-`. Publisher also: `--count`, `--rate-hz`,
`--payload-bytes`, `--seed`, `--start-delay-s` (discovery time), `--linger-s`. Subscriber also:
`--expected-count`, `--first-message-timeout-s`, `--idle-timeout-s`, `--overall-timeout-s`.
The subscriber exits 0 only for a clean complete run, 1 otherwise, 2 for bad arguments.

Untested assumptions in the adapters: the `std_msgs/ByteMultiArray` element handling and the
`rclpy` calls themselves.

## Limitations

* Counts messages only. It reports no latency, jitter, throughput or "resilience" figure, and this
  change contains no measurements.
* Non-actuating: it publishes numbered text on a topic you choose. Do not point it at a topic that
  drives hardware.
* Loss attribution (network, QoS history depth, discovery delay, subscriber start-up) is up to the
  experimenter; the probe only records what arrived. Late subscriber start-up shows up as head loss.
* One publisher and one subscriber per `run_id`; several subscribers produce separate streams
  keyed by node and topic.
* Python verification was done on 3.12 only.
