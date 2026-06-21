from collections.abc import Iterable

from kubek.kube import Container


def get_unique_ports(containers: Iterable[Container]) -> set[int]:
    """Unique container ports declared across the given containers."""
    return {
        port.container_port
        for container in containers
        for port in container.ports or []
    }
