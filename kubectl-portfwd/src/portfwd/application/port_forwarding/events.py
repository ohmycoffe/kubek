from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PortForwardProcessSnapshot:
    namespace: str
    service_name: str
    remote_port: int
    local_port: int
    pid: int
    returncode: int | None


@dataclass(frozen=True)
class PortForwardEvents:
    on_started: Callable[[PortForwardProcessSnapshot], None] = lambda snapshot: None
    on_stopped: Callable[[PortForwardProcessSnapshot], None] = lambda snapshot: None
    on_died: Callable[[PortForwardProcessSnapshot], None] = lambda snapshot: None
