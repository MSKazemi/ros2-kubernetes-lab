#!/usr/bin/env python3
"""rclpy publisher adapter for the sequence probe.  NOT RUN here: no ROS 2 in the authoring
environment. All message scheduling, payload building and logging live in the tested `seqprobe`
package; this file only creates a node/publisher and passes `publisher.publish` as `send`.

Example (inside the Jazzy image, after sourcing /opt/ros/jazzy/setup.bash):
    python3 rclpy_adapters/publisher_node.py --run-id r1 --count 100 --rate-hz 10 \
        --payload-bytes 64 --reliability reliable --depth 10 --log-file /tmp/pub.jsonl
"""

import argparse
import signal
import sys
import time

import _common
from seqprobe.clocks import Clocks
from seqprobe.config import GeneratorConfig, PublisherConfig
from seqprobe.errors import SeqProbeError
from seqprobe.runner import run_publisher
from seqprobe.sinks import JsonlSink


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    _common.add_common_args(p)
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--rate-hz", type=float, default=10.0)
    p.add_argument("--payload-bytes", type=int, default=64)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--start-delay-s", type=float, default=2.0,
                   help="wait after node creation before the first message (discovery time)")
    p.add_argument("--linger-s", type=float, default=2.0,
                   help="keep the node alive after the last message so reliable delivery can finish")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        gen = GeneratorConfig(run_id=args.run_id, count=args.count, rate_hz=args.rate_hz,
                              payload_bytes=args.payload_bytes, seed=args.seed, clock=args.clock)
        cfg = PublisherConfig(generator=gen, node=args.node_name or "seqprobe_pub",
                              topic=args.topic, start_delay_s=args.start_delay_s)
        qos = _common.qos_spec_from_args(args)
    except SeqProbeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    import rclpy  # lazy: only needed when actually running under ROS 2

    rclpy.init()
    node = rclpy.create_node(cfg.node)
    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("flag", True))
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("flag", True))
    try:
        msg_cls = _common.message_class(args.msg_type)
        pub = node.create_publisher(msg_cls, cfg.topic, qos.to_rclpy())
        clocks = Clocks(ros_now_ns=lambda: node.get_clock().now().nanoseconds)

        def send(payload):
            pub.publish(_common.wrap_payload(args.msg_type, payload))

        log = _common.open_log(args.log_file)
        try:
            run_publisher(cfg, send, JsonlSink(log), clocks, should_stop=lambda: stop["flag"],
                          extra_detail={"qos": qos.to_dict(), "msg_type": args.msg_type})
            time.sleep(args.linger_s)
        finally:
            if log is not sys.stdout:
                log.close()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
