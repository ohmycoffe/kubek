from dataclasses import dataclass


@dataclass(frozen=True)
class PortForwardProcessSnapshot:
    namespace: str
    service_name: str
    remote_port: int
    local_port: int
    pid: int
    returncode: int | None
