from dataclasses import dataclass

from portfwd.domain.models import TargetKind


@dataclass(frozen=True)
class PortForwardProcessSnapshot:
    kind: TargetKind
    namespace: str
    name: str
    remote_port: int
    local_port: int
    pid: int
    returncode: int | None
