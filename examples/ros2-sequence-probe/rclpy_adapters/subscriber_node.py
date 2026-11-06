#!/usr/bin/env python3
"""rclpy subscriber adapter for the sequence probe.  NOT RUN here: no ROS 2 in the authoring
environment. Decoding, sequence tracking, timeouts and logging live in the tested `seqprobe`
package; this file creates a node/subscription and forwards each message to a SubscriberSession.

Exit code: 0 = complete with no gap/duplicate/reordering, 1 = anything else (timeout, loss, ...),
2 = bad arguments.

Example (inside the Jazzy image, after sourcing /opt/ros/jazzy/setup.bash):
    python3 rclpy_adapters/subscriber_node.py --run-id r1 --expected-count 100 \
        --reliability reliable --depth 10 --log-file /tmp/sub.jsonl
"""

import argparse
import json
import sys

import _common
from seqprobe.clocks import Clocks
from seqprobe.config import SubscriberConfig
from seqprobe.errors import SeqProbeError
from seqprobe.runner import SubscriberSession
from seqprobe.sinks import JsonlSink


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    _common.add_common_args(p)
    p.add_argument("--expected-count", type=int, default=None,
                   help="messages the publisher will send; required to establish completion")
    p.add_argument("--first-message-timeout-s", type=float, default=30.0)
    p.add_argument("--idle-timeout-s", type=float, default=10.0)
    p.add_argument("--overall-timeout-s", type=float, default=300.0)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        cfg = SubscriberConfig(run_id=args.run_id, expected_count=args.expected_count,
                               node=args.node_name or "seqprobe_sub", topic=args.topic,
                               clock=args.clock,
                               first_message_timeout_s=args.first_message_timeout_s,
                               idle_timeout_s=args.idle_timeout_s,
                               overall_timeout_s=args.overall_timeout_s)
        qos = _common.qos_spec_from_args(args)
    except SeqProbeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    import rclpy  # lazy: only needed when actually running under ROS 2

    rclpy.init()
    node = rclpy.create_node(cfg.node)
    log = _common.open_log(args.log_file)
    try:
        clocks = Clocks(ros_now_ns=lambda: node.get_clock().now().nanoseconds)
        session = SubscriberSession(cfg, JsonlSink(log), clocks,
                                    extra_detail={"qos": qos.to_dict(), "msg_type": args.msg_type})
        session.start()
        node.create_subscription(_common.message_class(args.msg_type), cfg.topic,
                                 lambda msg: session.on_message(msg.data), qos.to_rclpy())
        try:
            while session.poll() == "running":
                rclpy.spin_once(node, timeout_sec=0.05)
        except KeyboardInterrupt:
            pass
        verdict = session.finish()
    finally:
        if log is not sys.stdout:
            log.close()
        node.destroy_node()
        rclpy.shutdown()
    print(json.dumps(verdict.to_dict(), sort_keys=True), file=sys.stderr)
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    sys.exit(main())
