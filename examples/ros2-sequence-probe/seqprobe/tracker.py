"""Subscriber-side sequence tracker: gaps, duplicates, reordering, completion/timeout verdicts.

Classification of each observed sequence number ``s`` (``next`` = highest seen + 1, or 0 at first):

* duplicate  - ``s`` was already received (counted regardless of position)
* unexpected - ``s`` < 0 or, when the expected count is known, ``s`` >= expected_count; not stored
* in_order   - ``s == next``
* gap        - ``s > next``: the sequence numbers in between are (so far) missing
* reordered  - ``s < next`` and never seen before: a late arrival that fills an earlier gap

At verdict time, *missing* = expected range (0..expected_count-1, or 0..highest when the count is
unknown) minus everything received. Tail loss (the last messages never arriving) can only be
detected when the expected count is known.
"""

from dataclasses import dataclass

from .errors import ConfigError

COMPLETIONS = ("complete", "timeout", "incomplete", "unknown")


@dataclass(frozen=True)
class Verdict:
    expected_count: int
    received_total: int
    unique: int
    duplicates: int
    reordered: int
    gap_events: int
    unexpected: int
    missing: int
    missing_ranges: tuple
    highest_seq: int
    completion: str
    ok: bool
    tail_loss_detectable: bool

    def to_dict(self):
        d = {name: getattr(self, name) for name in self.__dataclass_fields__}
        d["missing_ranges"] = [list(r) for r in self.missing_ranges]
        return d


class SequenceTracker:
    def __init__(self, expected_count=None):
        if expected_count is not None and (
            isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count < 1
        ):
            raise ConfigError(f"expected_count must be None or an integer >= 1 (got {expected_count!r})")
        self.expected_count = expected_count
        self._seen = set()
        self._highest = -1
        self.received_total = 0
        self.duplicates = 0
        self.reordered = 0
        self.gap_events = 0
        self.unexpected = 0

    @property
    def unique(self):
        return len(self._seen)

    def is_complete(self):
        return self.expected_count is not None and len(self._seen) == self.expected_count

    def observe(self, seq):
        """Record one reception; returns the classification string."""
        if isinstance(seq, bool) or not isinstance(seq, int):
            raise ConfigError(f"seq must be an integer (got {seq!r})")
        self.received_total += 1
        if seq < 0 or (self.expected_count is not None and seq >= self.expected_count):
            self.unexpected += 1
            return "unexpected"
        if seq in self._seen:
            self.duplicates += 1
            return "duplicate"
        nxt = self._highest + 1
        self._seen.add(seq)
        if seq == nxt:
            self._highest = seq
            return "in_order"
        if seq > nxt:
            self._highest = seq
            self.gap_events += 1
            return "gap"
        self.reordered += 1
        return "reordered"

    def _missing_ranges(self):
        limit = self.expected_count if self.expected_count is not None else self._highest + 1
        out = []
        prev = -1  # last present seq
        for s in sorted(self._seen):
            if s > prev + 1:
                out.append((prev + 1, s - 1))
            prev = s
        if prev + 1 < limit:
            out.append((prev + 1, limit - 1))
        return tuple(out)

    def verdict(self, timed_out=False):
        ranges = self._missing_ranges()
        missing = sum(b - a + 1 for a, b in ranges)
        if self.is_complete():
            completion = "complete"
        elif timed_out:
            completion = "timeout"
        elif self.expected_count is None:
            completion = "unknown"
        else:
            completion = "incomplete"
        ok = (completion == "complete" and self.duplicates == 0 and self.reordered == 0
              and self.unexpected == 0 and missing == 0)
        return Verdict(
            expected_count=self.expected_count,
            received_total=self.received_total,
            unique=len(self._seen),
            duplicates=self.duplicates,
            reordered=self.reordered,
            gap_events=self.gap_events,
            unexpected=self.unexpected,
            missing=missing,
            missing_ranges=ranges,
            highest_seq=self._highest,
            completion=completion,
            ok=ok,
            tail_loss_detectable=self.expected_count is not None,
        )
