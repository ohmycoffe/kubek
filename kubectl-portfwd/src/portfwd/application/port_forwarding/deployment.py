from kubek.kube import Deployment


def container_ports(deployment: Deployment) -> set[int]:
    """Unique container ports declared across all containers in a deployment template."""
    return {
        port.container_port
        for container in deployment.spec.template.spec.containers
        for port in container.ports
    }
