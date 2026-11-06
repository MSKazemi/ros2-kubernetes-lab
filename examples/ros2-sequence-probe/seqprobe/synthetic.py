"""SYNTHETIC end-to-end simulation driving the real publisher loop and subscriber session over an
in-memory channel with injected faults. Timestamps come from a virtual clock, so nothing here is
measured - the output is a deterministic fixture, labelled ``detail.synthetic = true``.
"""

from .clocks import Clocks
from .config import GeneratorConfig, PublisherConfig, SubscriberConfig
from .runner import run_publisher, SubscriberSession
from .sinks import ListSink

VIRTUAL_WALL_BASE_NS = 1_700_000_000_000_000_000
VIRTUAL_MONO_BASE_NS = 5_000_000_000_000
SYNTHETIC_DELIVERY_NS = 1_000_000  # fixed fake channel delay; NOT a measurement


class VirtualClocks(Clocks):
    """Time that only moves when someone sleeps or the channel 'delivers'."""

    def __init__(self):
        super().__init__(ros_now_ns=lambda: VIRTUAL_WALL_BASE_NS + self._offset)
        self._offset = 0

    def now_ns(self, clock):
        if clock == "monotonic":
            return VIRTUAL_MONO_BASE_NS + self._offset
        if clock in ("wall", "ros"):
            return VIRTUAL_WALL_BASE_NS + self._offset
        return super().now_ns(clock)

    def sleep(self, seconds):
        self._offset += round(seconds * 1e9)

    def advance_ns(self, ns):
        self._offset += ns


def simulate(run_id="synthetic", count=10, rate_hz=10.0, payload_bytes=64, seed=0, clock="wall",
             drop=(), duplicate=(), swap=(), expect_count=True, node_pub="seqprobe_pub",
             node_sub="seqprobe_sub", topic="/seqprobe", idle_timeout_s=2.0):
    """Return ``(events, verdict)``.

    drop       seqs the channel never delivers
    duplicate  seqs delivered twice
    swap       seqs ``a`` delivered after ``a + 1`` (adjacent swap)
    """
    clocks = VirtualClocks()
    sink = ListSink()
    gen = GeneratorConfig(run_id=run_id, count=count, rate_hz=rate_hz, payload_bytes=payload_bytes,
                          seed=seed, clock=clock)
    pub_cfg = PublisherConfig(generator=gen, node=node_pub, topic=topic)
    sub_cfg = SubscriberConfig(run_id=run_id, expected_count=count if expect_count else None,
                               node=node_sub, topic=topic, clock=clock,
                               first_message_timeout_s=idle_timeout_s, idle_timeout_s=idle_timeout_s,
                               overall_timeout_s=max(idle_timeout_s * 10, count / rate_hz * 10 + 10))
    sub = SubscriberSession(sub_cfg, sink, clocks, extra_detail={"synthetic": True})
    sub.start()

    drop, duplicate, swap = set(drop), set(duplicate), set(swap)
    held = []

    def deliver(payload):
        clocks.advance_ns(SYNTHETIC_DELIVERY_NS)
        sub.on_message(payload)

    def send(payload):
        from .payload import decode_payload

        seq = decode_payload(payload).seq
        if seq in drop:
            return
        if seq in swap:
            held.append(payload)
            return
        deliver(payload)
        if seq in duplicate:
            deliver(payload)
        while held:
            deliver(held.pop(0))

    run_publisher(pub_cfg, send, sink, clocks, extra_detail={"synthetic": True})
    while held:
        deliver(held.pop(0))
    state = sub.poll()
    if state == "running":
        clocks.advance_ns(round(idle_timeout_s * 1e9))
        state = sub.poll()
    verdict = sub.finish()
    return sink.events, verdict
