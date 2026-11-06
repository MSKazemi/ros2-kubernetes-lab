"""Exception types for the sequence probe. All derive from ValueError so callers can
catch one family of "bad input" problems."""


class SeqProbeError(ValueError):
    """Base class for every error raised by this package."""


class ConfigError(SeqProbeError):
    """A command-line / configuration value is invalid (rate, count, payload size, ...)."""


class PayloadError(SeqProbeError):
    """A received payload is not a well-formed probe payload."""


class LogFormatError(SeqProbeError):
    """A JSON-lines log record violates the schema. Carries the 1-based line number."""

    def __init__(self, message, line_no=None):
        self.line_no = line_no
        prefix = f"line {line_no}: " if line_no is not None else ""
        super().__init__(prefix + message)


class ClockMismatchError(SeqProbeError):
    """Two timestamps from different clock domains were about to be combined."""
