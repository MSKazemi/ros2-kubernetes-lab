"""Explicit clock domains.

Three clocks exist and they are never mixed silently:

* ``monotonic`` - ``time.monotonic_ns()``. Per-process/per-host, never jumps backwards, and its
  origin is arbitrary. Values from two different nodes are NOT comparable.
* ``wall``      - ``time.time_ns()``, nanoseconds since the Unix epoch (UTC). Comparable across
  nodes only to the accuracy of their clock synchronisation, which this tool does not measure.
* ``ros``       - ``node.get_clock().now()``. System time unless ``use_sim_time`` is set, in
  which case it is simulated time. Only available inside the rclpy adapters.

Every timestamped record carries the name of its clock next to the value.
"""

from .errors import ClockMismatchError, ConfigError

CLOCKS = ("monotonic", "wall", "ros")

CLOCK_DESCRIPTIONS = {
    "monotonic": "time.monotonic_ns(); arbitrary origin; comparable only within one node",
    "wall": "time.time_ns(); Unix epoch UTC; comparable across nodes only up to clock sync error",
    "ros": "rclpy node clock now(); system or simulated time depending on use_sim_time",
}


def check_clock_name(name, what="clock"):
    if not isinstance(name, str) or name not in CLOCKS:
        raise ConfigError(f"{what} must be one of {', '.join(CLOCKS)} (got {name!r})")
    return name


def require_same_clock(clock_a, clock_b, node_a=None, node_b=None):
    """Raise ClockMismatchError unless a timestamp difference between the two is meaningful."""
    if clock_a != clock_b:
        raise ClockMismatchError(
            f"cannot combine timestamps from different clocks ({clock_a} vs {clock_b})"
        )
    if clock_a == "monotonic" and node_a != node_b:
        raise ClockMismatchError(
            f"monotonic timestamps from different nodes are not comparable ({node_a!r} vs {node_b!r})"
        )


class Clocks:
    """Source of timestamps. ``ros_now_ns`` is a callable supplied by the rclpy adapters."""

    def __init__(self, ros_now_ns=None):
        self._ros_now_ns = ros_now_ns

    def now_ns(self, clock):
        import time

        check_clock_name(clock)
        if clock == "monotonic":
            return time.monotonic_ns()
        if clock == "wall":
            return time.time_ns()
        if self._ros_now_ns is None:
            raise ConfigError("clock 'ros' needs a ROS node clock; it is only available in the rclpy adapters")
        return int(self._ros_now_ns())

    def sleep(self, seconds):
        import time

        time.sleep(seconds)
