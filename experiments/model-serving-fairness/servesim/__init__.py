"""servesim: deterministic CPU-only discrete-event simulation of a shared
model-serving node under multi-robot contention. All output is SIMULATED."""

from .config import ConfigError, SimConfig, parse_config
from .engine import SimResult, simulate
from .metrics import jain_index, percentile_nearest_rank, summarize

__all__ = ["ConfigError", "SimConfig", "SimResult", "parse_config", "simulate",
           "summarize", "jain_index", "percentile_nearest_rank"]
