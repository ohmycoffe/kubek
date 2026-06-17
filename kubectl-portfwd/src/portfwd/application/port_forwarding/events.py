from dataclasses import dataclass
from enum import StrEnum

from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot


class OutputStream(StrEnum):
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass(frozen=True)
class OutputLine:
    """A single line of subprocess output and which stream it came from."""

    stream: OutputStream
    text: str


@dataclass(frozen=True)
class PortForwardStarted:
    """A port-forward subprocess has started running."""

    snapshot: PortForwardProcessSnapshot


@dataclass(frozen=True)
class PortForwardStopped:
    """A port-forward subprocess was stopped as part of an expected shutdown."""

    snapshot: PortForwardProcessSnapshot


@dataclass(frozen=True)
class PortForwardDied:
    """A port-forward subprocess exited unexpectedly and will be restarted."""

    snapshot: PortForwardProcessSnapshot


@dataclass(frozen=True)
class PortForwardOutput:
    """A line of stdout/stderr from a running port-forward subprocess."""

    snapshot: PortForwardProcessSnapshot
    output: OutputLine


@dataclass(frozen=True)
class PortForwardReconnecting:
    """A restart is blocked because the local port is still in use."""

    namespace: str
    service_name: str
    remote_port: int
    local_port: int


@dataclass(frozen=True)
class PortForwardLaunchFailed:
    """An attempt to launch the port-forward failed; ``reason`` is the error."""

    namespace: str
    service_name: str
    remote_port: int
    local_port: int
    reason: str


PortForwardEvent = (
    PortForwardStarted
    | PortForwardStopped
    | PortForwardDied
    | PortForwardOutput
    | PortForwardReconnecting
    | PortForwardLaunchFailed
)
"""Everything the streamer yields to the presentation layer about a port-forward.

A closed set of standalone events; consumers discriminate with ``match`` /
``isinstance``. The user-facing wording is the presentation layer's job.
"""
