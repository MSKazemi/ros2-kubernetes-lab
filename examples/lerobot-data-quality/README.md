# LeRobot data-quality contract for SYNTHETIC ROS 2 episodes (issue #93)

> **Synthetic, offline, non-actuating.** This directory validates the *metadata and tiny numeric frames* of **100% synthetic** robot episodes with the Python standard library. It does **not** import or run LeRobot, torch or `huggingface_hub`, does **not** write a LeRobotDataset, and does **not** show that a Hugging Face upload or reload works. The contract field names are this project's own; they are not asserted to equal the on-disk layout of any LeRobot release. Nothing here is a benchmark, a model result or a safety gate.

## Why

A dataset conversion that silently accepts a 5-value action, a `deg` where `rad` was meant, a jittering timestamp or a missing camera produces a dataset that loads but trains on wrong data. This contract states the checks *before* any conversion, so the failure is a clear diagnostic with a code and a hint instead of a downstream surprise. It reuses the joint layout (six joints, `rad`, gripper in `m`, limits) and the two camera keys of the simulated observation/action contract in [`examples/cloud-robotics/mock-policy/`](../cloud-robotics/mock-policy/) (`ros2-obs-action/v1`); a test compares the two whenever both directories exist.

## Quick start (CPU only, no network, about a second)

From the repository root, Python 3.10 or newer:

```sh
# run the tests
python3 -m unittest discover -s examples/lerobot-data-quality/tests -t examples/lerobot-data-quality -v

# validate a good file (exit 0) and a bad one (exit 1)
python3 examples/lerobot-data-quality/dq_validate.py examples/lerobot-data-quality/fixtures/valid/synthetic_3ep_10fps.json
python3 examples/lerobot-data-quality/dq_validate.py examples/lerobot-data-quality/fixtures/invalid/unit_mismatch.json

# machine-readable report, list of all codes, fixture drift check
python3 examples/lerobot-data-quality/dq_validate.py --format json FILE.json
python3 examples/lerobot-data-quality/dq_validate.py --list-codes
python3 examples/lerobot-data-quality/fixture_gen.py --check
```

Example output for an invalid file:

```text
FAIL fixtures/invalid/unit_mismatch.json
  [UNIT_MISMATCH] /features/observation.state/units/5: gripper: unit 'mm', contract requires 'm'
      hint: Use the unit from the contract table (rad for joints, m for gripper).
0 valid, 1 invalid (synthetic-episodes-meta/v1)
```

Exit codes: `0` all files valid, `1` at least one invalid (including unparseable JSON), `2` usage error or unreadable file. The validator never raises on bad input; an unexpected internal error becomes `INTERNAL_ERROR` (invalid). Files are limited to 1 MiB and reports to 100 diagnostics per file.

## Files

| File | Purpose |
| --- | --- |
| [`dq_contract.py`](dq_contract.py) | Constants and the table of diagnostic codes. Data only. |
| [`dq_validate.py`](dq_validate.py) | Validator (`validate_document/text/file`) and CLI. |
| [`schema/synthetic-episodes.v1.schema.json`](schema/synthetic-episodes.v1.schema.json) | JSON Schema (2020-12) documenting the structure. A test keeps its constants in sync; the Python validator is the executable authority (JSON Schema cannot express the timestamp, boundary and per-joint checks). |
| [`fixture_gen.py`](fixture_gen.py) | Deterministic generator for [`fixtures/`](fixtures/) (closed-form sine waves, no randomness). `--check` detects drift. |
| [`fixtures/valid/`](fixtures/valid/), [`fixtures/invalid/`](fixtures/invalid/) | 2 valid and 26 invalid fixtures, each invalid one a single mutation. [`expected_diagnostics.json`](fixtures/expected_diagnostics.json) gives the one code and first path each must produce. |
| [`fixtures/LICENSE-NOTE.md`](fixtures/LICENSE-NOTE.md) | Fixtures are synthetic and CC0-1.0; code is under the repository licence. |
| [`tests/`](tests/) | `unittest` suite (positive, negative, robustness, CLI, fixture hygiene). |

## Contract `synthetic-episodes-meta/v1`

One JSON object per dataset:

| Field | Rule | Code on violation |
| --- | --- | --- |
| `schema_version` | must equal `synthetic-episodes-meta/v1`; an unknown version stops validation (the rest of its layout is not guessed) | `SCHEMA_VERSION_UNKNOWN`, `MISSING_FIELD` |
| `synthetic` | exactly `true` | `NOT_SYNTHETIC` |
| `license` | required SPDX id from `CC0-1.0, Apache-2.0, MIT, CC-BY-4.0, CC-BY-SA-4.0, BSD-3-Clause` | `LICENSE_MISSING`, `LICENSE_NOT_ALLOWED` |
| `dataset_name` | non-empty string | `MISSING_FIELD` |
| `fps` | integer 1..1000 | `FPS_INVALID` |
| `timestamp_tolerance_s` | optional; number in (0, 0.5/fps); default 0.001 | `TOLERANCE_INVALID` |
| `features["observation.state"]`, `features["action"]` | `dtype` `float32`; `shape` `[6]`; `names` = `shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper`; `units` = `rad` x5, `m` (gripper) | `FEATURE_MISSING`, `FEATURE_DTYPE_BAD`, `FEATURE_SHAPE_BAD`, `DIM_MISMATCH`, `FEATURE_NAMES_MISMATCH`, `UNIT_MISMATCH` |
| `features["observation.images.front"]`, `...wrist` | `dtype` `video` or `image`; `names` `[height, width, channels]`; `shape` `[h, w, c]` agreeing with the `camera` block; `camera` = `width`, `height` (1..1024), `encoding` (`rgb8` 3 ch, `mono8` 1 ch), `fps` (= dataset fps). Extra `observation.images.*` features are checked the same way. **Metadata only: no pixel payload.** | `CAMERA_METADATA_MISSING`, `CAMERA_METADATA_INVALID`, `FEATURE_*` |
| `tasks[]` | non-empty list of `{task_index, task}`; unique indices; non-blank description; each episode's `task_index` must exist | `TASK_MISSING` |
| `episodes[]` | non-empty list | `NO_EPISODES` |
| `episodes[].episode_index` | unique (`EPISODE_INDEX_DUPLICATE`) and exactly 0..N-1 in order (`EPISODE_INDEX_GAP`) | |
| `episodes[].frames` | at least one frame, else `EPISODE_EMPTY` (no frames at all); `length` must be an integer equal to `len(frames)`, else `EPISODE_LENGTH_MISMATCH` (this includes `length: 0` with frames present) | `EPISODE_EMPTY`, `EPISODE_LENGTH_MISMATCH`, `WRONG_TYPE` |
| `episodes[].dataset_from_index/to_index` | first episode starts at 0; each starts where the previous one ended; `to - from` = number of frames | `EPISODE_BOUNDARY_GAP` |
| `frames[].frame_index` | equals the position in the episode | `FRAME_INDEX_MISMATCH` |
| `frames[].observation.state`, `action` | exactly 6 finite numbers inside the per-joint limits (`shoulder_pan`/`wrist_roll` +-3.1416, `shoulder_lift`/`elbow_flex` +-1.7, `wrist_flex` +-1.8 rad, `gripper` 0..0.08 m) | `DIM_MISMATCH`, `WRONG_TYPE`, `NON_FINITE_VALUE`, `OUT_OF_LIMITS` |
| `frames[].timestamp` | seconds; **strictly increasing** within an episode (equal values rejected); and `abs(t - frame_index/fps) <= tolerance` | `TIMESTAMP_NOT_MONOTONIC`, `TIMESTAMP_FPS_DRIFT` |

Notes on the timestamp rules. Drift is only evaluated on strictly increasing timestamps and a valid `fps`, so one root cause yields one kind of diagnostic. Timestamps are per-episode (frame 0 is expected at 0 s); that is a choice of *this* contract. `NaN`/`Infinity` literals are rejected at parse time.

Type confusion. Every value taken from the document is type-checked before it is used in a set, dict or comparison lookup, so a list or object in a scalar field (for example `task_index`, camera `encoding`, `dtype`, a unit, `schema_version`) yields `WRONG_TYPE` with the field's path, and validation of the remaining episodes and frames continues. Integers too large for a float are reported as `NON_FINITE_VALUE`. `INTERNAL_ERROR` stays only as a last-resort fail-closed net; a test that replaces and deletes every node of a valid document with hostile values asserts it never fires.

Every diagnostic has `code`, `severity`, `path` (RFC 6901 JSON pointer), `message` and `hint`; `--list-codes` prints the full table.

### What the tests cover

Every invalid case from the issue has a fixture and a named test: dimension mismatch (frame vector, feature shape, names/units), unit mismatch, non-monotonic timestamp, fps drift, missing camera metadata (block, field and whole feature), empty episode, duplicate episode index, bad and missing licence, unknown schema version. Also: non-synthetic flag, blank task, out-of-limit values, invalid fps/tolerance, episode gaps and boundary gaps, `length: 0` with frames, lists/objects in lookup fields (`WRONG_TYPE`, later episodes still checked), a mutation sweep over every node (never `INTERNAL_ERROR`), hostile shapes (never raise), oversize and deeply nested input, diagnostic cap, the CLI exit codes and JSON report, fixture size (< 10 KB each, no image data) and generator drift.

## Documented, NOT RUN: real LeRobotDataset v3 conversion

**Nothing in this section has been executed.** No `lerobot` package, no `huggingface_hub`, no Hub repository and no network were used to produce this directory. It is a plan, to be carried out and verified in a separate step.

1. **Select and verify the pin.** *Pin to be selected and verified before implementation.* Look up the current stable official LeRobot release and the dataset format version it writes (the issue targets LeRobotDataset v3), record both with the date, and pin them exactly in a requirements file for the conversion script only. Do not infer them from this README.
2. **Keep this validator as the gate.** Convert only files for which `dq_validate.py` exits `0`, so the conversion never receives metadata this contract rejects.
3. **Write with the official API.** Build the dataset with the pinned release's own dataset-creation and episode-saving API (do not hand-write its parquet/video/metadata files). Map: `fps` -> dataset fps, `features` -> feature specs, `tasks[].task` -> per-frame task string, frames -> `observation.state` / `action`. Camera features require actual frames: generate tiny synthetic images deterministically (for example gradients) in the conversion step; none exist here. Method and argument names must be read from the pinned release's documentation, not from this file.
4. **Mandatory reload test (the acceptance criterion).** After writing, load the dataset in a fresh process through the pinned release's public loader and assert: number of episodes and frames equal the source; per-frame `observation.state` and `action` equal the source within float32 precision; feature names, shapes and dtypes equal the contract; per-episode lengths and boundaries match; fps matches; decoded camera frames have the declared resolution; the task strings round-trip. A conversion that has not passed this reload test must not be described as working.
5. **Hub card (draft only).** State: synthetic, generated by `fixture_gen.py`-style code, no real robot or person data, licence (CC0-1.0 or the repository licence), the pinned LeRobot version and the reload test result with its date, and that the data is for pipeline testing and not for training or benchmarking. Check the Hub's accepted licence identifiers and card format at upload time; they may differ from SPDX spelling used here.
6. **Upload is a separate, explicitly approved step.** Publishing is outward-facing and may be cached or indexed; do not upload without the owner's approval, and review the dataset contents first.

Open questions for step 1: whether the contract's per-episode timestamps and `dataset_from_index/to_index` map one-to-one onto the pinned release's metadata (they may be derived rather than written), and whether the pinned release accepts `dtype` `image` and/or `video` for the camera features at conversion time.

## Limitations

- Checks metadata and tiny numeric frames only; **no pixel data** is read or generated, so camera `shape`/`encoding` are declarations, not verified images.
- Not a LeRobotDataset schema and not verified against any LeRobot release; passing here does not imply a successful conversion, load, upload or training run.
- The fixed six-joint layout is the one from the simulated `ros2-obs-action/v1` contract. Other robots need another profile (change `dq_contract.py` and the schema together).
- Value checks are range checks, not physics: a smooth but impossible trajectory passes. Velocity or jerk limits are not checked.
- `license` is a self-declared string checked against an allow-list. It is not legal advice and not provenance.
- The `synthetic` flag is a declaration; the validator cannot prove that data is not real.
- Non-actuating: nothing here talks to ROS 2, a robot, Kubernetes or DDS, and it provides no evidence about cross-node delivery.

## Related

Issue #93 (this work), epic #92, related #56, #57, #58; the observation/action contract in [`docs/OBSERVATION-ACTION-CONTRACT.md`](../../docs/OBSERVATION-ACTION-CONTRACT.md) and [`examples/cloud-robotics/mock-policy/`](../cloud-robotics/mock-policy/) (on `main`).
