"""Where events go: an in-memory list (tests) or a JSON-lines text stream (files / stdout)."""

from .events import Event


class ListSink:
    def __init__(self):
        self.events = []

    def emit(self, event):
        if not isinstance(event, Event):
            raise TypeError("sink.emit expects an Event")
        self.events.append(event)


class JsonlSink:
    """Writes one schema-v1 JSON line per event and flushes each line (so `kubectl logs` and
    `tail -f` show events as they happen)."""

    def __init__(self, stream):
        self._stream = stream

    def emit(self, event):
        if not isinstance(event, Event):
            raise TypeError("sink.emit expects an Event")
        self._stream.write(event.to_json_line() + "\n")
        self._stream.flush()
