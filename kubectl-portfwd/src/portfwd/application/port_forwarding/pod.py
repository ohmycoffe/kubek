from kubek.kube import Pod


def container_ports(pod: Pod) -> set[int]:
    """Unique container ports declared on a pod."""
    return {
        port.container_port
        for container in pod.spec.containers
        for port in container.ports
    }
