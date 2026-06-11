from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class PortForwardProcessSnapshot:
    namespace: str
    service_name: str
    remote_port: int
    local_port: int
    pid: int
    returncode: int | None


class PortForwardEventType(StrEnum):
    STARTED = "started"
    STOPPED = "stopped"
    DIED = "died"


@dataclass(frozen=True)
class PortForwardEvent:
    type: PortForwardEventType
    snapshot: PortForwardProcessSnapshot

    @property
    def exited(self) -> bool:
        """True when the port-forward subprocess has exited (stopped or died)."""
        return self.type in (
            PortForwardEventType.STOPPED,
            PortForwardEventType.DIED,
        )
