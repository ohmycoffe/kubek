from dataclasses import dataclass
from enum import StrEnum

from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.domain.models import TargetKind


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
    """Waiting to relaunch after an unexpected exit or launch failure."""

    kind: TargetKind
    namespace: str
    name: str
    remote_port: int
    local_port: int
    attempt: int


@dataclass(frozen=True)
class PortForwardLocalPortBusy:
    """Waiting for the local port to become available before relaunching."""

    kind: TargetKind
    namespace: str
    name: str
    remote_port: int
    local_port: int
    poll: int


@dataclass(frozen=True)
class PortForwardLaunchFailed:
    """An attempt to launch the port-forward failed; ``reason`` is the error."""

    kind: TargetKind
    namespace: str
    name: str
    remote_port: int
    local_port: int
    reason: str
    attempt: int


@dataclass(frozen=True)
class PortForwardLaunchAbandoned:
    """Launch retries are exhausted and this forward will not be restarted."""

    kind: TargetKind
    namespace: str
    name: str
    remote_port: int
    local_port: int
    max_retries: int


PortForwardEvent = (
    PortForwardStarted
    | PortForwardStopped
    | PortForwardDied
    | PortForwardOutput
    | PortForwardReconnecting
    | PortForwardLocalPortBusy
    | PortForwardLaunchFailed
    | PortForwardLaunchAbandoned
)
"""Everything the streamer yields to the presentation layer about a port-forward.

A closed set of standalone events; consumers discriminate with ``match`` /
``isinstance``. The user-facing wording is the presentation layer's job.
"""
