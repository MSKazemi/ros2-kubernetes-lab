# Experiment status registry

**Purpose:** one page that says, for every experiment or experiment-shaped artifact in this repository, what exists, what kind of evidence it produces, how to re-run its check, and what it does **not** show. It is the evidence registry and artifact contract requested in [#88](https://github.com/MSKazemi/robo-resilience-lab/issues/88) and part of the drift control in [#44](https://github.com/MSKazemi/robo-resilience-lab/issues/44). The experiment plan itself lives in the [experiment portfolio](EXPERIMENT-PORTFOLIO.md) and the roadmap in [ROADMAP-2026.md](ROADMAP-2026.md); this page does not replace either. Pinned versions are in the [version matrix](VERSION-MATRIX.md).

> **Read this first.** This is an educational/research lab. Nothing below has controlled a robot, and **no entry reports a measured latency, throughput, GPU, accuracy or benchmark figure for ROS 2, DDS, Kubernetes or a model.** Where a number appears, it is a count of tests, or an output of a labelled SIMULATION or SYNTHETIC generator. The only entry with a *measured* run is the kind baseline, and it is one run on one host.

## Status vocabulary

| Status | Meaning | May quote a number as a finding about a real system? |
|---|---|---|
| `planned` | In a roadmap or issue; no code in the repository | No |
| `implemented-offline` | Code and tests run on a laptop with no cluster, GPU, robot or network; inputs are checked-in or generated fixtures | No (fixtures describe the generator, not a system) |
| `simulated` | A model of a system produces the numbers | No (shows how the *model* behaves under assumed parameters) |
| `measured` | Recorded from a real run, with command, host, date and exit code written down | Only for that run, that host and that configuration |

`SYNTHETIC` marks generated input data. `SIMULATION` marks model output. Definitions are also in the [glossary](GLOSSARY.md#experiment-status-labels).

## Summary

| Card | Experiment | Issues | Status | Where | Check (exit code, this review) |
|---|---|---|---|---|---|
| [A](#a-kind-baseline-ros-2-delivery-across-workers) | Kind baseline: ROS 2 delivery across workers (E02 baseline) | #14, #15, #16 | `measured` (once, one host) | `Makefile`, `kind/`, `docs/KIND-DEMO.md` on public `main` | `make verify`: **not run here** |
| [B](#b-e02-dds-resilience-under-impairment-offline-harness) | E02 DDS resilience under impairment | #48, #18 | `implemented-offline` (SYNTHETIC traces) | `experiments/e02-dds-resilience/` | 49 tests OK, exit 0 |
| [C](#c-sequence-probe) | ROS 2 sequence probe | #52 | `implemented-offline` core; ROS adapters **not run** | `examples/ros2-sequence-probe/` | 66 tests OK, exit 0 |
| [D](#d-edgecloud-inference-placement) | Edge/cloud inference placement | #85, #62 | `simulated` | `experiments/edge-cloud-placement/` | 44 tests OK, exit 0 |
| [E](#e-lerobot-data-quality) | LeRobot data quality (E03 precursor) | #93, #92 | `implemented-offline` (SYNTHETIC episodes) | `examples/lerobot-data-quality/` | 42 tests OK (1 skipped), exit 0 |
| [F](#f-model-serving-fairness) | Model-serving fairness and cache placement (E07) | #107, #69, #87 | `simulated` | `experiments/model-serving-fairness/` | 56 tests OK, exit 0 |
| [G](#g-agent-mobility-e08) | Agent mobility, mission-state handoff (E08) | #104, #110 | `simulated` (offline toy) | `docs/cloud-robotics/agent-mobility/`, `examples/cloud-robotics/agent-mobility/` | 60 tests OK, exit 0 |
| [H](#h-observationaction-contract-and-mock-policy-e00) | Observation/action contract and MOCK policy (E00) | #55 | `implemented-offline` (simulated, non-actuating) | `examples/cloud-robotics/mock-policy/` on public `main` | 84 tests OK, exit 0 (read-only copy of `main`) |

**How the "this review" column was produced.** On 2026-11-06 the technical-docs role ran each command in the "Test command" row of its card from the repository root with `python3 -m unittest` (Python 3.12, standard library, no network, no cluster) and read the exit code. Cards B to G describe directories that were still being written by other roles in the same working tree and were **not yet committed**; re-run before relying on a count. Card H was run against a read-only copy of public `main` because the branch tree does not contain it. Docker, kind and Kubernetes were not used in this review.

**Links valid only after the rebase onto public `main`:** `KIND-DEMO.md`, `EXPERIMENT-PORTFOLIO.md`, `OBSERVATION-ACTION-CONTRACT.md` and `examples/cloud-robotics/mock-policy/README.md` exist on `main` but not on the current branch tree.

**Not in the registry yet (`planned`, no code):** E01 local-classifier incident triage (#74, #75, #84, #94), E04 zero-shot perception placement (#106), E06 SmolVLA simulation evaluation (#95), E09 energy/cost/quality frontier (#70). Their design is in the [experiment portfolio](EXPERIMENT-PORTFOLIO.md). E05 (action freshness versus continuity) has only the simulated precursor in card D.

---

## A. Kind baseline: ROS 2 delivery across workers

| Field | Value |
|---|---|
| Status | `measured`: one run, one host, kindnetd CNI. Support state `cross-worker verified` for this profile only ([definitions](ROS2-KUBERNETES-DDS-GUIDE.md#support-states-and-evidence)) |
| Where | `Makefile`, `kind/ros2k8s-demo.yaml`, `ROS2/jazzy/talker-listener.yaml`, `scripts/verify-ros2.sh`, [`docs/KIND-DEMO.md`](KIND-DEMO.md) (all on public `main`) |
| Test command | `make demo`, then `make verify` (exit 0 only if pods are Ready, on different workers, and the listener's counter advances and matches the talker's own log); `make verify-negative` proves the check can fail |
| Recorded evidence | Commit `862b026`, 2026-10-27, one host (12 logical CPUs, 31 GB RAM, Docker 29.9.2, kind v0.33.0, Kubernetes v1.37.0): `make demo` exit 0 (82 s warm), `make verify` exit 0, `make verify-negative` exit 0, as written in `docs/KIND-DEMO.md` |
| This review | **Not re-run.** The numbers are quoted from that page. Its GitHub Actions workflow (`.github/workflows/kind-demo.yml`) had not been executed when the page was written; this review did not check GitHub for a run (no network access was used) |
| NOT claimed | Vagrant/kubeadm/Weave Net; any other CNI; a multi-machine cluster; arm64, macOS, Windows; QoS other than the demo defaults; behaviour on restart; any latency or throughput |
| Negative results (recorded on that page) | Default Fast DDS multicast discovery delivered **0** messages on kindnetd, across two workers and also on one worker. A plain UDP probe showed unicast crossed workers and multicast to `239.255.0.1` timed out. A listener on `ROS_DOMAIN_ID=43` still heard the domain-42 talker through the shared Discovery Server, so domain IDs do not isolate clients of one server. With a very large open-files limit a talker was OOM-killed at a 256Mi limit; the cause was not established |
| Related single-host evidence | Fourteen Docker-bridge discovery tests (Fast DDS server on/off, `ROS_DOMAIN_ID` mismatch, Cyclone with and without peers, static peers) are tabulated in the [DDS guide](ROS2-KUBERNETES-DDS-GUIDE.md). They are not Kubernetes evidence |

## B. E02 DDS resilience under impairment (offline harness)

| Field | Value |
|---|---|
| Status | `implemented-offline`. All fixtures are **SYNTHETIC**; **no live experiment has been run** |
| Where | [`experiments/e02-dds-resilience/`](../experiments/e02-dds-resilience/README.md): `matrix/matrix.yaml` (2 reliability x 6 impairment = 12 cells), `ddsres/` (trace validation and metrics), `fixtures/` (12 generated traces + `MANIFEST.json`), `tests/` |
| Test command | `python3 -m unittest discover -s experiments/e02-dds-resilience/tests -t experiments/e02-dds-resilience`. Also: `python3 experiments/e02-dds-resilience/run.py validate-matrix` and `... run.py check-fixtures` |
| This review | Tests: 49 run, OK, exit 0. `validate-matrix`: "matrix OK: 12 cells", exit 0. `check-fixtures`: every fixture printed `ok`, exit 0 |
| NOT claimed | Any behaviour of Fast DDS, Cyclone DDS or Zenoh; any cross-node, kind or Kubernetes result; any DDS-versus-Zenoh comparison (no run exists for any RMW); that the live `tc netem` recipe works (it is flagged NOT RUN and never executed by this code) |
| Negative results / limits | None measured. The owner adds that fault markers need an operator-supplied file because probe schema v1 has none, and monotonic clocks from two nodes are refused as mixed domains. Per the README: the synthetic checks are circular on purpose (they confirm the analyzer reads a fixture as its generator intended); a latency p99 from fewer than 100 samples equals the maximum and is reported as unresolved; malformed, truncated, clock-mixed or empty traces are rejected rather than guessed |
| Depends on | Card C (reads its schema-v1 event log) and card A (the baseline a live run would start from) |

## C. Sequence probe

| Field | Value |
|---|---|
| Status | `implemented-offline` for the `seqprobe/` core (message plan, payload format, tracker, offline analysis, synthetic fault simulation). The `rclpy` publisher/subscriber adapters are **NOT RUN** |
| Where | [`examples/ros2-sequence-probe/`](../examples/ros2-sequence-probe/README.md). Complements, and does not replace, the `ros2_pulse` rate counters described in [`ROS2/jazzy/README.md`](../ROS2/jazzy/README.md) (issue #52) |
| Test command | `python3 -m unittest discover -s examples/ros2-sequence-probe/tests -t examples/ros2-sequence-probe` |
| This review | 66 tests run, OK, exit 0. `python3 -m seqprobe simulate --count 20 --drop 5,6 --duplicate 9 --swap 12 --out FILE` printed "SYNTHETIC log: 44 events, completion=timeout, ok=False" (exit 0); `python3 -m seqprobe analyze FILE` reported 2 missing (range 5-6), 1 duplicate, 1 reordered and exited **1**, which is the documented exit code for "not ok" |
| NOT claimed | Any DDS or Kubernetes delivery; any latency, jitter or throughput (the tool never subtracts send from receive time); that the adapters work (they were written without a ROS installation and only checked to import and to reject bad arguments); any Kubernetes manifest (none is included) |
| Negative results / limits | Without `--expected-count` messages lost at the end of a run cannot be seen, so the verdict is never `ok`. Late subscriber start-up shows up as head loss, which the probe cannot attribute to a cause. The schema has no restart or fault-marker events. The `ByteMultiArray` handling and the `rclpy` calls are untested. Verified on Python 3.12 only |

## D. Edge/cloud inference placement

| Field | Value |
|---|---|
| Status | `simulated`. Output is labelled SIMULATION, carries `"measured": false`, and every sink decision has `"actuated": false` |
| Where | [`experiments/edge-cloud-placement/`](../experiments/edge-cloud-placement/README.md): `placement_sim.py`, `configs/default.json`, `reports/default.summary.json` and `default.table.txt`, `tests/` |
| Test command | `python3 -m unittest discover -s experiments/edge-cloud-placement/tests -t experiments/edge-cloud-placement`. Run: `python3 experiments/edge-cloud-placement/placement_sim.py --config experiments/edge-cloud-placement/configs/default.json` |
| This review | 44 tests run, OK, exit 0. The default-config run (seed 20261106, exit 0) printed the same four-policy table as the README |
| NOT claimed | Any property of a real robot, network, cloud service, GPU, DDS stack or cluster. The parameters are illustrative placeholders; none was measured |
| Negative results (SIMULATED, default config) | `always_remote` was the worst policy: on-time rate 0.7000 against 0.9167 for `always_local`. `deadline_aware` (0.8567) did worse than `always_local`. `hedged_fallback` was best at 0.9333, a gain of about 1.7 percentage points over `always_local`, and the README reports it launched 135 local fallback runs to rescue 29 requests. These results hold for the stated model and parameters only; other parameters may reorder the policies. The owner adds that the remote helps only for the tightest deadlines in this sample (stated by the owner; not checked here) |
| Limits | Logical-time toy: unlimited remote capacity, i.i.d. loss and jitter, perfect shared clocks, no GPU, bandwidth or energy model. The README lists seven things a real measurement would need (all NOT RUN) |

## E. LeRobot data quality

| Field | Value |
|---|---|
| Status | `implemented-offline`. 100 percent **SYNTHETIC** episodes; metadata and tiny numeric frames only |
| Where | [`examples/lerobot-data-quality/`](../examples/lerobot-data-quality/README.md): `dq_contract.py`, `dq_validate.py`, `schema/synthetic-episodes.v1.schema.json`, `fixtures/` (2 valid, 21 invalid), `tests/` |
| Test command | `python3 -m unittest discover -s examples/lerobot-data-quality/tests -t examples/lerobot-data-quality -v`. Also `python3 examples/lerobot-data-quality/fixture_gen.py --check` |
| This review | 42 tests run, OK with 1 skipped, exit 0. The skipped test compares the joint layout with `examples/cloud-robotics/mock-policy`, which is not in the branch tree (it is on `main`); it will run after integration. `fixture_gen.py --check` printed "fixtures up to date" |
| NOT claimed | That LeRobot, `torch` or `huggingface_hub` was imported or run; that a LeRobotDataset v3 was written, reloaded or uploaded; that pixel data is valid (no pixels are read); that passing implies a successful conversion, upload or training run |
| Negative results / limits | Each of the 21 invalid fixtures is a single mutation with one expected code (for example `UNIT_MISMATCH`, `TIMESTAMP_FPS_DRIFT`, `EPISODE_INDEX_GAP`). The owner confirms nothing was installed or run from LeRobot, `torch` or `huggingface_hub`. With `examples/cloud-robotics/mock-policy` present (as on `main`) the skipped test is reported to pass. Range checks only, not physics: a smooth but impossible trajectory passes. The `synthetic` flag and the licence string are declarations the validator cannot verify. The real conversion plan is documented and **NOT RUN**; the LeRobot version pin is still to be selected |

## F. Model-serving fairness

| Field | Value |
|---|---|
| Status | `simulated`. CPU-only discrete-event simulation; no model is loaded and no GPU is used |
| Where | [`experiments/model-serving-fairness/`](../experiments/model-serving-fairness/README.md): `run_simulation.py`, `servesim/`, `data/default_fleet.json`, `tests/` |
| Test command | `python3 -m unittest discover -s experiments/model-serving-fairness/tests -t experiments/model-serving-fairness`. Run: `python3 experiments/model-serving-fairness/run_simulation.py` |
| This review | 56 tests run, OK, exit 0. The default run (seeds 1, 2, 3; FIFO, EDF, DRR; two placements) exited 0 and printed a table labelled SIMULATED |
| NOT claimed | Any real model latency, GPU memory behaviour, batching, network, DDS or Kubernetes behaviour. Service times, load costs, cache sizes, deadlines and arrival rates are assumed parameters |
| Negative results (SIMULATED, default scenario, seeds 1 to 3, as printed in this review) | DRR cut the overall deadline-miss rate (about 16 to 17 percent against about 25 to 27 percent for FIFO) and the quiet-client miss rate (about 1 percent against about 17 to 19 percent), **but** it raised p95 and p99 latency (p99 about 2.5 to 2.8 s against about 1.9 to 2.2 s for FIFO), lowered Jain's goodput index (about 0.92 against about 0.97) and produced more starved requests (57 to 69 against 14 to 20). `cache_aware` and `first_idle` placement gave identical rows in this scenario; the README says placement only matters when two or more workers are idle at once and ships `data/cache_pressure.json` for that case (the owner reports cache hit rates of about 77 to 80 percent with `cache_aware` against about 48 to 51 percent with `first_idle` there, FIFO, seeds 1 and 2; not re-run here). The owner also reports that in overloaded retunings of the scenario all schedulers miss about 99 percent of deadlines (not re-run here). A handful of seeds gives no confidence intervals |

## G. Agent mobility (E08)

| Field | Value |
|---|---|
| Status | `simulated`: an offline toy that validates and replays a `mission-state/v1` handoff bundle. It is **not** an implementation of robot or agent migration |
| Where | Specification: [`docs/cloud-robotics/agent-mobility/`](cloud-robotics/agent-mobility/README.md) (schema, compatibility matrix, "what is not moved", fencing rules, failure-case catalogue). Code and fixtures: [`examples/cloud-robotics/agent-mobility/`](../examples/cloud-robotics/agent-mobility/README.md) (`mission_state.py`, `validate_bundle.py`, `handoff_sim.py`, `fixture_gen.py`, `fixtures/`, `tests/`) |
| Test command | `python3 -m unittest discover -s examples/cloud-robotics/agent-mobility/tests -v` (the command in that directory's README). Also `python3 examples/cloud-robotics/agent-mobility/validate_bundle.py`, `... handoff_sim.py` and `... fixture_gen.py --check`; do not use `python3 -I`, which removes the script directory from the import path |
| This review | 60 tests run, OK, exit 0. `validate_bundle.py`, `handoff_sim.py` and `fixture_gen.py --check` each exited 0 |
| NOT claimed | A process, container, model or actuation right moving between machines; any ROS 2, Kubernetes or cross-host handoff; any latency or success-rate figure (time is logical ticks, not milliseconds); authenticated transport (the digest is a plain SHA-256, not a signature); a durable coordinator. The design was written without assuming draft PR #109 is merged |
| Negative results / limits | The simulator is meant to **refuse** stale-epoch, replayed, expired, digest-mismatched and incompatible bundles; the fixture set includes cases such as `digest-mismatch`, `bundle-expired`, `bundle-from-future` and `action-units-mismatch`, each listed in the failure-case catalogue as a case that must be refused. Rejections are the tested behaviour, not a performance result. The owner reports 42 typed rejection reasons, each with a fixture, and a documented list of 12 uncovered cases (coordinator crash, forged bundles, clock skew, partitions, physical effects already emitted, and others). Passing tests validate a toy; they are not a research result, and the results registry for E08 stays at `planned` / `null` |

## H. Observation/action contract and MOCK policy (E00)

| Field | Value |
|---|---|
| Status | `implemented-offline`: a simulated, non-actuating validator and a seeded MOCK policy with no task accuracy |
| Where | [`examples/cloud-robotics/mock-policy/`](../examples/cloud-robotics/mock-policy/README.md) and [`docs/OBSERVATION-ACTION-CONTRACT.md`](OBSERVATION-ACTION-CONTRACT.md), both on public `main` (issue #55) |
| Test command | `python3 -m unittest discover -s examples/cloud-robotics/mock-policy/tests`; `python3 examples/cloud-robotics/mock-policy/fixture_gen.py --check` (run it without `python3 -I`, which removes the script directory from the import path) |
| This review | Against a read-only copy of `main`: 84 tests OK, exit 0; fixture drift check exit 0 |
| NOT claimed | ROS 2 adapter (deferred), any model, GPU or network use, Kubernetes or DDS behaviour, authentication (`source_id` is a label compared with an allow-list), a safety-certified gate |
| Negative results / limits | Every typed rejection (`STALE_ACTION`, `DUPLICATE_SEQUENCE`, `OUT_OF_LIMITS`, `UNAUTHORIZED_SOURCE`, and others) has a positive and a negative test. The allow-list is empty by default, so all actions are rejected until one is configured |

---

## Artifact contract and run card (issue #88)

An experiment may be listed above as `measured` only if a **run card** like the one below is committed next to its raw output. A run card makes a result reproducible and makes missing evidence visible. Fields marked required may be `null`; they may not be omitted or guessed.

| Field | Required | Rule |
|---|---|---|
| `id`, `title` | yes | Registry card letter or portfolio id (for example `E02`), and a short title |
| `status` | yes | One of the four values above |
| `labels` | yes | `SYNTHETIC` and/or `SIMULATION` when they apply; otherwise `[]` |
| `repo_commit` | yes | Full commit hash of the tree that was run; a dirty tree must say so |
| `date`, `host` | yes | UTC date; CPU count, RAM, OS and kernel, container runtime, kind and Kubernetes versions as run |
| `command`, `exit_code` | yes | The exact command and its exit code, copied from the terminal |
| `inputs` | yes | File paths and sha256 of every fixture, config and image digest used; seeds |
| `outputs` | yes | File paths and sha256 of every artifact produced |
| `numbers_are` | yes | `counts`, `synthetic`, `simulated` or `measured`. A table of numbers without this field is not a result |
| `not_claimed` | yes | At least one explicit sentence |
| `negative_results` | yes | What failed, was worse than the baseline, or could not be run. "None" must be justified |
| `repeats`, `variability` | for `measured` | Number of repeats and a spread (for example min and max); one run is stated as one run |
| `reviewed_by` | no | A human reviewer, when there is one |

Template (copy into `<experiment>/reports/RUN-<date>.md`; do not use the directory names `results/`, `runs/`, `measurements/` or `findings/`, which the public firewall ignores):

```markdown
# Run card: <id> <title>
- status: measured | simulated | implemented-offline
- labels: [SYNTHETIC | SIMULATION]
- repo_commit: <40 hex> (clean | dirty)
- date (UTC) / host: <date> / <cpus, RAM, OS, kernel, docker, kind, kubernetes>
- command: `<exact command>`   exit_code: <n>
- inputs: <path sha256>, seed <n>, image digest <sha256:...>
- outputs: <path sha256>
- numbers_are: counts | synthetic | simulated | measured
- not_claimed: <one or more sentences>
- negative_results: <what failed, or why none>
- repeats / variability: <n> / <min..max> (measured only)
```

## Re-checking this page

The commands in each card are the single source of truth. To refresh the "this review" column, run them again from the repository root and update the counts and exit codes in the same pull request that changes an experiment. Link integrity of this page is checked with `python3 scripts/check-markdown-links.py` (local links and anchors only; no network).
