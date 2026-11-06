"""QoS options as plain, validated data. Conversion to rclpy objects is lazy (rclpy optional)."""

from dataclasses import dataclass, asdict

from .errors import ConfigError

RELIABILITIES = ("reliable", "best-effort")
DURABILITIES = ("volatile", "transient-local")
MAX_DEPTH = 10_000


@dataclass(frozen=True)
class QosSpec:
    reliability: str = "reliable"
    depth: int = 10
    durability: str = "volatile"

    def __post_init__(self):
        if self.reliability not in RELIABILITIES:
            raise ConfigError(f"reliability must be one of {', '.join(RELIABILITIES)} (got {self.reliability!r})")
        if self.durability not in DURABILITIES:
            raise ConfigError(f"durability must be one of {', '.join(DURABILITIES)} (got {self.durability!r})")
        if isinstance(self.depth, bool) or not isinstance(self.depth, int) or not (1 <= self.depth <= MAX_DEPTH):
            raise ConfigError(f"depth must be an integer in 1..{MAX_DEPTH} (got {self.depth!r})")

    def to_dict(self):
        return asdict(self)

    def to_rclpy(self):
        """Build an rclpy QoSProfile (KEEP_LAST history). Imports rclpy lazily; needs ROS."""
        from rclpy.qos import (QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy,
                               QoSHistoryPolicy)

        return QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=self.depth,
            reliability=(QoSReliabilityPolicy.RELIABLE if self.reliability == "reliable"
                         else QoSReliabilityPolicy.BEST_EFFORT),
            durability=(QoSDurabilityPolicy.VOLATILE if self.durability == "volatile"
                        else QoSDurabilityPolicy.TRANSIENT_LOCAL),
        )
