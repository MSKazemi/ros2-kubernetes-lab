# Beginner guide: the simulated observation/action contract

> **Simulated, educational, non-actuating.** This contract checks messages in plain Python. It does not control a robot, run ROS 2, call an AI model, or prove anything about Kubernetes or DDS. It is not a safety-certified gate.

## The idea in one minute

A robot-AI pipeline passes two messages: an **observation** (camera images plus joint state) goes to a policy, and the policy returns an **action** (target joint values). If the data is wrong, old, from the wrong sender or not a number, a program should **refuse it and say why**, never guess. This module writes that rule down as a *contract* and checks it with a *validator* that does not depend on any model code.

```text
fixture (synthetic) -> validate observation -> MOCK policy -> validate action -> printed only (no dispatch)
```

The MOCK policy is a few lines of seeded arithmetic. It has no accuracy and must not be reported as a result.

## Try it (no ROS, GPU, network or VM)

From the repository root, with Python 3.10 or newer:

```sh
python3 -m unittest discover -s examples/cloud-robotics/mock-policy/tests -v
python3 examples/cloud-robotics/mock-policy/example.py
```

The first command runs the positive and negative tests. The second prints the accepted observation, the accepted action and then the *same action replayed*, which is rejected with `DUPLICATE_SEQUENCE`.

## What gets rejected

Missing or mistyped fields, a missing camera, a camera name whose key does not match the mapping, wrong image shape, wrong joint order or units, the wrong number of values, values outside a joint's limits, NaN or infinity, timestamps that are out of bounds or go backwards, a repeated sequence number, an action older than the configured maximum age, a source that is not on the allow-list, and any command other than `set_joint_targets`. Each rejection returns a typed reason such as `STALE_ACTION`; the validator does not raise on bad input.

## Where to go next

- Reference, file list and the full table of reasons: [examples/cloud-robotics/mock-policy/README.md](../examples/cloud-robotics/mock-policy/README.md).
- Good first changes: add one more negative test, or a new rejection reason with a test that fails without it. Weaken a check on purpose and confirm a test fails before you restore it.
- Not covered yet: a ROS 2 Jazzy adapter (waits for a verified fixture/topic mapping), fault injection and safe-stop semantics in simulation (issue #59), and any cross-worker evidence (issues #14, #15, #16).
