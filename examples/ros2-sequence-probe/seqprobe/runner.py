"""Pure-Python publisher loop and subscriber session. No ROS imports.

The rclpy adapters supply the transport: a ``send(payload_text)`` callable for the publisher and
calls to ``SubscriberSession.on_message`` / ``poll`` for the subscriber. Tests supply fakes.

Timeouts always use the monotonic clock regardless of which clock is written to the log, so a
wall-clock step cannot cause or hide a timeout.
"""

from .clocks import Clocks, CLOCK_DESCRIPTIONS
from .config import config_to_dict
from .errors import PayloadError
from .events import Event
from .generator import plan, payload_for
from .payload import decode_payload
from .tracker import SequenceTracker

_NS = 1_000_000_000


def _event(cfg_run_id, role, node, topic, kind, ts_ns, clock, **kw):
    return Event(event=kind, role=role, run_id=cfg_run_id, node=node, topic=topic,
                 ts_ns=ts_ns, clock=clock, **kw)


def run_publisher(cfg, send, sink, clocks=None, should_stop=None, extra_detail=None):
    """Send ``cfg.generator.count`` messages on schedule; log start/send/stop. Returns a summary.

    ``ts_ns`` of a send event is read immediately before ``send`` is called. If ``send`` raises,
    a stop event with reason "error" is logged and the exception propagates.
    """
    clocks = clocks or Clocks()
    should_stop = should_stop or (lambda: False)
    g = cfg.generator
    ident = (g.run_id, "publisher", cfg.node, cfg.topic)

    detail = {"config": config_to_dict(cfg), "expected_count": g.count,
              "clock_description": CLOCK_DESCRIPTIONS[g.clock], "synthetic": False}
    if extra_detail:
        detail.update(extra_detail)
    sink.emit(_event(*ident, "start", clocks.now_ns(g.clock), g.clock, detail=detail))

    if cfg.start_delay_s:
        clocks.sleep(cfg.start_delay_s)

    sent = 0
    reason = "completed"
    t0 = clocks.now_ns("monotonic")
    try:
        for msg in plan(g):
            wait_ns = t0 + msg.offset_ns - clocks.now_ns("monotonic")
            if wait_ns > 0:
                clocks.sleep(wait_ns / _NS)
            if should_stop():
                reason = "stopped"
                break
            ts = clocks.now_ns(g.clock)
            payload = payload_for(g, msg.seq, ts)
            send(payload)
            sink.emit(_event(*ident, "send", ts, g.clock, seq=msg.seq, payload_bytes=len(payload)))
            sent += 1
    except BaseException:
        sink.emit(_event(*ident, "stop", clocks.now_ns(g.clock), g.clock,
                         detail={"sent": sent, "reason": "error"}))
        raise
    sink.emit(_event(*ident, "stop", clocks.now_ns(g.clock), g.clock,
                     detail={"sent": sent, "reason": reason}))
    return {"sent": sent, "reason": reason}


class SubscriberSession:
    """Receives raw payloads, logs recv events, tracks the sequence, applies timeouts.

    Typical use::

        s = SubscriberSession(cfg, sink); s.start()
        ... s.on_message(raw) from the subscription callback ...
        ... state = s.poll() periodically; stop when state != "running" ...
        verdict = s.finish()
    """

    def __init__(self, cfg, sink, clocks=None, extra_detail=None):
        self.cfg = cfg
        self.sink = sink
        self.clocks = clocks or Clocks()
        self.tracker = SequenceTracker(cfg.expected_count)
        self.malformed = 0
        self.foreign_run = 0
        self.timed_out = False
        self._extra = extra_detail or {}
        self._ident = (cfg.run_id, "subscriber", cfg.node, cfg.topic)
        self._t_start = None
        self._t_last = None
        self._finished = False

    def start(self):
        detail = {"config": config_to_dict(self.cfg), "expected_count": self.cfg.expected_count,
                  "clock_description": CLOCK_DESCRIPTIONS[self.cfg.clock], "synthetic": False}
        detail.update(self._extra)
        self.sink.emit(_event(*self._ident, "start", self.clocks.now_ns(self.cfg.clock),
                              self.cfg.clock, detail=detail))
        self._t_start = self.clocks.now_ns("monotonic")

    def on_message(self, raw):
        """Handle one received payload. Returns the tracker classification, or
        "malformed" / "foreign_run" for payloads that are not part of this run."""
        if self._t_start is None:
            raise RuntimeError("SubscriberSession.start() must be called first")
        ts = self.clocks.now_ns(self.cfg.clock)
        try:
            dec = decode_payload(raw)
        except PayloadError:
            self.malformed += 1
            return "malformed"
        if dec.run_id != self.cfg.run_id:
            self.foreign_run += 1
            return "foreign_run"
        self._t_last = self.clocks.now_ns("monotonic")
        kind = self.tracker.observe(dec.seq)
        self.sink.emit(_event(*self._ident, "recv", ts, self.cfg.clock, seq=dec.seq,
                              payload_bytes=dec.payload_bytes, sent_ts_ns=dec.sent_ts_ns,
                              sent_clock=dec.sent_clock))
        return kind

    def poll(self):
        """Return "complete", "timeout" or "running"; logs one timeout event on the first timeout."""
        if self._t_start is None:
            raise RuntimeError("SubscriberSession.start() must be called first")
        if self.tracker.is_complete():
            return "complete"
        if self.timed_out:
            return "timeout"
        now = self.clocks.now_ns("monotonic")
        cfg = self.cfg
        reason = None
        if now - self._t_start >= cfg.overall_timeout_s * _NS:
            reason = "overall"
        elif self._t_last is None:
            if now - self._t_start >= cfg.first_message_timeout_s * _NS:
                reason = "first_message"
        elif now - self._t_last >= cfg.idle_timeout_s * _NS:
            reason = "idle"
        if reason is None:
            return "running"
        self.timed_out = True
        self.sink.emit(_event(*self._ident, "timeout", self.clocks.now_ns(cfg.clock), cfg.clock,
                              detail={"reason": reason, "received_unique": self.tracker.unique}))
        return "timeout"

    def finish(self):
        """Log the stop event (verdict inside ``detail``) and return the Verdict."""
        verdict = self.tracker.verdict(timed_out=self.timed_out)
        if not self._finished:
            self._finished = True
            self.sink.emit(_event(*self._ident, "stop", self.clocks.now_ns(self.cfg.clock),
                                  self.cfg.clock,
                                  detail={"verdict": verdict.to_dict(), "malformed": self.malformed,
                                          "foreign_run": self.foreign_run}))
        return verdict
