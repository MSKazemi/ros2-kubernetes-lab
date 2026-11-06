"""Per-worker model cache with LRU eviction (size-aware)."""

from __future__ import annotations

from collections import OrderedDict
from typing import List


class ModelCache:
    """LRU cache of model ids bounded by total ``size`` units.

    ``access`` is the only operation that changes recency: a hit moves the
    model to the most-recently-used end; a miss evicts least-recently-used
    models until the new model fits, then inserts it.
    """

    def __init__(self, capacity: float):
        if not capacity > 0:
            raise ValueError("capacity must be > 0")
        self.capacity = capacity
        self._items: "OrderedDict[str, float]" = OrderedDict()
        self.used = 0.0
        self.evictions = 0

    def __contains__(self, model: str) -> bool:
        return model in self._items

    def resident(self) -> List[str]:
        """Resident model ids, least recently used first."""
        return list(self._items)

    def free(self) -> float:
        return self.capacity - self.used

    def access(self, model: str, size: float) -> bool:
        """Touch ``model``. Returns True on hit, False on miss (after loading)."""
        if model in self._items:
            self._items.move_to_end(model)
            return True
        if size > self.capacity:
            raise ValueError(f"model {model!r} of size {size} exceeds capacity {self.capacity}")
        while self.used + size > self.capacity + 1e-12:
            _victim, vsize = self._items.popitem(last=False)
            self.used -= vsize
            self.evictions += 1
        self._items[model] = size
        self.used += size
        return False

    def clear(self) -> None:
        self._items.clear()
        self.used = 0.0
