"""Shared helpers for the rclpy adapters. NOT RUN in the authoring environment (no ROS there).

Importing this module does not import rclpy; the adapters import it lazily inside main().
"""

import argparse
import os
import sys

# Make the sibling `seqprobe` package importable when a script is run directly
# (python3 rclpy_adapters/publisher_node.py ...) without installing anything.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from seqprobe.clocks import CLOCKS  # noqa: E402
from seqprobe.qos import RELIABILITIES, DURABILITIES, QosSpec  # noqa: E402

MSG_TYPES = ("string", "bytes")


def add_common_args(parser):
    parser.add_argument("--run-id", required=True, help="[A-Za-z0-9_-]{1,32}; must match on both sides")
    parser.add_argument("--topic", default="/seqprobe")
    parser.add_argument("--node-name", default=None)
    parser.add_argument("--msg-type", choices=MSG_TYPES, default="string",
                        help="string = std_msgs/String, bytes = std_msgs/ByteMultiArray")
    parser.add_argument("--clock", choices=CLOCKS, default="wall",
                        help="clock written to every log record (see README, 'Clock semantics')")
    parser.add_argument("--reliability", choices=RELIABILITIES, default="reliable")
    parser.add_argument("--durability", choices=DURABILITIES, default="volatile")
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--log-file", default="-", help="JSON-lines output; '-' = stdout")


def qos_spec_from_args(args):
    return QosSpec(reliability=args.reliability, depth=args.depth, durability=args.durability)


def open_log(path):
    return sys.stdout if path == "-" else open(path, "w", encoding="utf-8")


def message_class(msg_type):
    if msg_type == "string":
        from std_msgs.msg import String
        return String
    from std_msgs.msg import ByteMultiArray
    return ByteMultiArray


def wrap_payload(msg_type, payload):
    """Payload text -> message instance."""
    cls = message_class(msg_type)
    msg = cls()
    if msg_type == "string":
        msg.data = payload
    else:
        msg.data = [bytes([b]) for b in payload.encode("ascii")]
    return msg
