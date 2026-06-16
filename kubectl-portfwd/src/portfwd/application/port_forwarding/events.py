from dataclasses import dataclass
from enum import StrEnum

from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot


class PortForwardEventType(StrEnum):
    STARTED = "started"
    STOPPED = "stopped"
    DIED = "died"
    OUTPUT = "output"
    SESSION_DONE = "session_done"


class OutputStream(StrEnum):
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass(frozen=True)
class OutputLine:
    """A single line of subprocess output and which stream it came from."""

    stream: OutputStream
    text: str


@dataclass(frozen=True)
class PortForwardEvent:
    type: PortForwardEventType
    snapshot: PortForwardProcessSnapshot
    output: OutputLine | None = None

    @property
    def is_control(self) -> bool:
        """True for internal coordination events not meant for the UI."""
        return self.type == PortForwardEventType.SESSION_DONE
