# Research benchmarks and reproducibility contract

> This is a **method specification**. No new inference, ROS/K8s placement, energy or robotics benchmark measurements have been run for this documentation. Historical plots under [DataAnalysis](../../DataAnalysis/) must remain labeled historical, and broken recovery measurement logic is tracked in [#45](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/45).

## Why robotics needs more than model latency

A policy forward pass is only one segment of the robotics decision chain. A valid engineering or research result should distinguish:

- Source observation capture at the ROS node.
- ROS publish/deliver/discovery and subscriber queue delay.
- Observation encoding/preprocessing, request/transport scheduling.
- Inference queueing, processor/model time and action chunk generation.
- Response transport, de-serialization and **deterministic validation**.
- Simulator application or *actual* task completion (only with compatible model and simulator).
- Fallback/hold/reject event on disconnection, stale output or incompatible action.

**Kubernetes container restart time ≠ recovery of a valid robotics action. ROS receiver callback count ≠ independent end-to-end delivery proof. A model-generated action tensor ≠ robot task success.**

## Measurement contract

| Metric | Definition | Unit / interpretation |
| --- | --- | --- |
| `delivery_ratio` | unique accepted sequence IDs / emitted IDs in defined window | %; report dropped/duplicate counts and window limits |
| `discovery_time_ms` | controlled start-to-first confirmed subscription delivery | ms; document what starts/stops the clock |
| `capture_to_request_ms` | time between observation capture and policy request submission | ms, same-clock or synchronized with known offset |
| `request_rtt_ms` | client-local elapsed request send → usable model response | ms monotonic, includes network + queue + inference |
| `inference_server_ms` | server-local pre/post processing + model compute, distinctly instrumented | ms monotonic on server |
| `candidate_action_age_ms` | accepted action time − source observation timestamp | ms; only comparable with valid clock mapping |
| `validator_latency_ms` | request candidate → gate decision | ms monotonic |
| `deadline_miss_rate` | requests/outcomes older than preregistered target | %; target specific to simulator/task, not safety certified |
| `action_starvation_s` | total time available action queue is exhausted | s/episode; distinguish holding vs no motor output |
| `sim_task_success` | externally defined simulated task success | successes / valid episodes; don't invent task labels |
| `recovery_to_usable_policy_s` | fault injection → first independently verified valid policy response | s, not pod-ready time |
| `cpu_peak_mib` / `rss_peak_mib` | observed host/pod resource measurement | MiB and source instrument |
| `gpu_vram_peak_mib` | actually measured GPU memory where available | MiB, else N/A |
| `energy_j` | measured power integrated over explicit system/time boundary | joules; else N/A (CPU% is not energy) |
| `cost_per_valid_task` | dated tariff + measured runtime / valid task completion | currency/task with assumptions |
| `blocked_action_count` | reason-coded validator denials | count per seed/test run |
| `trace_completeness` | expected timestamped stages with valid IDs / expected stages | %, report missing probes |

**Statistics:** report p50/p95/p99 with sample count and variability. P99 from a handful of requests can be misleading; publish full tail traces and the sample size required for a credible tail claim. Compare repeated independent runs (≥3 as a minimal initial floor, more as variance/power analysis indicates), not thousands of correlated samples from only one run.

## Clock discipline and causal attribution

1. Use **monotonic time for durations within one process/host**; never compute intervals by subtracting monotonic clocks from different hosts.
2. Cross-host timestamps require a declared synchronization method (e.g. NTP/PTP), verified offset and uncertainty, or a different client-local RTT method. Record simulation clock separately from wall time.
3. Trace IDs must propagate through ROS observation, policy request/response, action gate and simulator acceptance/rejection.
4. Keep network impairment injector seed, start/end, actual measured RTT/loss and buffer state, not only configured tc command.
5. Clearly separate transport/protocol traces from application success and from model task outcomes.

## Artifact manifest (illustrative JSON, no executable schema yet)

```json
{
  "manifest_version": "cloud-robotics-run-v0-proposal",
  "run_id": "synthetic-example-NOT-measured",
  "status": "fixture_only",
  "utc_start": "2026-10-27T00:00:00Z",
  "source_repo": "MSKazemi/Vagrant-Kubernetes-ROS2-Deployment",
  "source_commit": "EXAMPLE_COMMIT_REQUIRED",
  "container_digest": "EXAMPLE_SHA256_REQUIRED",
  "ros_distro": "jazzy",
  "ros_rmw": "RECORD_ACTUAL_RMW",
  "kubernetes": "NOT_APPLICABLE_FOR_OFFLINE_FIXTURE",
  "cni": "NOT_APPLICABLE",
  "simulator": {"name": "synthetic-only", "scene_revision": "fixture-v1"},
  "policy": {"kind": "mock", "revision": "mock-v1", "action_semantics": "sim_rad_v1"},
  "dataset": {"id": "synthetic-fixture", "revision": "fixture-v1", "license": "REVIEW_REQUIRED"},
  "hardware": {"arch": "RECORD_ACTUAL", "cpu": "RECORD_ACTUAL", "gpu": null},
  "network": {"placement": "local", "delay_ms": 0, "loss_pct": 0, "seed": 17},
  "clock": {"duration": "single_host_monotonic", "cross_host_offset_ms": null},
  "trial": {"condition_id": "cpu-mock", "seed": 17, "repetition": 1},
  "outcomes": {"success": null, "failure_reason": "NOT_TESTED"},
  "raw_results_path": "FILL_AFTER_ACTUAL_RUN",
  "reproduction_command": "FILL_AFTER_IMPLEMENTATION"
}
```

**Never substitute these illustrative values for actual measurements.** Define a real JSON Schema and tests in [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60). Include artifact hashes, provenance and exact configuration/CI run URLs in completed manifests. Avoid logging raw customer/participant data.

## Experiment lifecycle

1. **Preregister:** research question, null/alternative, reference implementation, independent/dependent variables, failure criteria, exclusion rules, threshold units and test hardware.
2. **Review:** model/dataset license and compatibility, public data/privacy risk, permissions, safety boundaries and third-party code.
3. **Freeze:** source/image/model/dataset versions, ROS/RMW/CNI/K8s, QoS, simulator seed/scene, camera/action semantics, workload rate.
4. **Sanity:** small successful local fixture and deliberate failing input. Cross-worker/remote experiment requires actual cluster evidence.
5. **Collect:** randomized treatment order if feasible; independent trials; latency histogram and full failure logs; every omission recorded with reason.
6. **Analyze:** version-controlled scripts regenerate charts and confidence intervals/uncertainty; inspect outliers rather than deleting bad runs.
7. **Reproduce:** a second person or CI environment follows an explicitly documented script from a clean environment. Keep the **raw** and **processed** results separate.
8. **Release:** research note with reproducibility level, exact status, limitations, privacy/licensing checks, citations and release decision.

## Three reproducibility levels

| Level | Evidence | Can say |
| --- | --- | --- |
| R0: static specification | Architecture + source with no runtime proof | "proposed", "design", "unverified" |
| R1: offline test | schema/fixture/readback or CPU mock test in CI, pinned versions | "offline fixture validated" |
| R2: integrated lab | fresh supported cluster with distinct workers, real messaging/policy request and logs | "lab-integrated on documented hardware" |
| R3: replicated research | independent reruns with raw data, variance, seeds and analysis | "reproduced for this experimental setup" |

Do **not** claim a physical certification/real-time SLA at any of these levels. R2+ refers to a particular tested profile, not all platforms.

## Recommended initial study designs

### B1: Robot middleware baseline
Control: one published message size/rate with explicit discovery and QoS. Treatments: node restart, alternative protocol/config in [#48](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/48). Record delivery ratio, discovery, restarts, CPU and packet loss. Do not silently combine DDS and LeRobot remote Zenoh as if they were the same component.

### B2: Model placement/freshness
Control: same model, checkpoint and simulator; local synchronous baseline. Treatments: local async where supported; server same LAN; Kubernetes server, with explicit impairment. Track action age and validity, starvation, task success and full inference request times. Avoid comparing different hardware without labels.

### B3: Offline/cached recovery
Control: fixed pinned checkpoint with warm cache. Treatments: absent cache, corrupted cache, image redeploy, network offline and restart. Measure time to usable policy result, bytes, failures and cache integrity.

### B4: LLM skill authorization
Control: deterministic task parser. Treatments: LLM-generated proposals with/without schema validation; read-only RAG. Count attempted invalid calls and **executed** violations separately; include injection corpus and legitimate false rejects.

### B5: Energy and fairness
Only after B2 has reliable instrumentation. Compare multi-client contention and local/remote cost/energy per **successful** task, with actual power measurement; do not infer it from CPU usage alone.

## Publications and reproducibility artifacts

- Per-run manifest JSON and config; exact source/image/model/dataset digests or commit revisions.
- A small public **licensed** input fixture with checksums, expected output and schema checks.
- Raw CSV/JSON/Parquet event records with declared units, missing values and failures.
- Plotting/analysis code (dependencies locked), figures regenerated from raw records.
- Report with hypotheses and baselines, time windows, warmups, resource budget, CI/clean-run proof, confidence intervals/dispersion, negative results and threats to validity.
- Model/dataset cards, safety/risk register, optional read-only demo.
- Academic citation and related work (FogROS2, robotics benchmarking, LeRobot) rather than ungrounded novelty marketing.

Use [experiment template](templates/EXPERIMENT-TEMPLATE.md). Existing benchmark issue [#18](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/18) owns the general DDS/monitoring suite; [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60) adds this AI policy/run contract.
