"""seqprobe - sequence-ID probe core for ROS 2 topics. Pure standard library; ROS is optional.

The ROS-facing pieces live in ``../rclpy_adapters`` and import rclpy lazily. Everything in this
package is testable on a machine without ROS installed.
"""

from .events import SCHEMA_VERSION, Event, read_events
from .tracker import SequenceTracker, Verdict
from .analysis import analyze_events

__all__ = ["SCHEMA_VERSION", "Event", "read_events", "SequenceTracker", "Verdict", "analyze_events"]
__version__ = "0.1.0"
