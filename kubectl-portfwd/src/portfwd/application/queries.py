import itertools
from collections.abc import Iterable

from kubek.kube import Deployment, Pod, Service
from portfwd.application.port_forwarding.deployment import (
    container_ports as deployment_container_ports,
)
from portfwd.application.port_forwarding.pod import (
    container_ports as pod_container_ports,
)
from portfwd.application.ports import KubeGateway
from portfwd.domain.models import (
    PortForwardSpec,
    TargetKind,
    TargetRef,
)


def _convert_services_to_specs(
    services: Iterable[Service],
) -> list[PortForwardSpec]:
    """Flatten Service list to (target, remote_port) specs, sorted for the picker."""
    return [
        PortForwardSpec(
            target=TargetRef(
                kind=TargetKind.SERVICE,
                namespace=svc.metadata.namespace,
                name=svc.metadata.name,
            ),
            remote_port=port.port,
        )
        for svc in sorted(
            services, key=lambda s: (s.metadata.namespace, s.metadata.name)
        )
        for port in sorted(svc.spec.ports, key=lambda x: x.port)
    ]


def _convert_pods_to_specs(
    pods: Iterable[Pod],
) -> list[PortForwardSpec]:
    """Flatten Pod list to (target, remote_port) specs, one per declared container port."""
    return [
        PortForwardSpec(
            target=TargetRef(
                kind=TargetKind.POD,
                namespace=pod.metadata.namespace,
                name=pod.metadata.name,
            ),
            remote_port=container_port,
        )
        for pod in sorted(pods, key=lambda p: (p.metadata.namespace, p.metadata.name))
        for container_port in sorted(pod_container_ports(pod))
    ]


def fetch_services_for_namespaces(
    namespaces: list[str], api: KubeGateway
) -> list[PortForwardSpec]:
    raw = itertools.chain.from_iterable(
        api.service.list(namespace=ns) for ns in namespaces
    )
    return _convert_services_to_specs(raw)


def fetch_pods_for_namespaces(
    namespaces: list[str], api: KubeGateway
) -> list[PortForwardSpec]:
    raw = itertools.chain.from_iterable(api.pod.list(namespace=ns) for ns in namespaces)
    return _convert_pods_to_specs(raw)


def _convert_deployments_to_specs(
    deployments: Iterable[Deployment],
) -> list[PortForwardSpec]:
    """Flatten Deployment list to (target, remote_port) specs, one per declared container port."""
    return [
        PortForwardSpec(
            target=TargetRef(
                kind=TargetKind.DEPLOYMENT,
                namespace=deployment.metadata.namespace,
                name=deployment.metadata.name,
            ),
            remote_port=container_port,
        )
        for deployment in sorted(
            deployments, key=lambda d: (d.metadata.namespace, d.metadata.name)
        )
        for container_port in sorted(deployment_container_ports(deployment))
    ]


def fetch_deployments_for_namespaces(
    namespaces: list[str], api: KubeGateway
) -> list[PortForwardSpec]:
    """Fetch deployments with declared container ports for the picker."""
    raw = itertools.chain.from_iterable(
        api.deployment.list(namespace=ns) for ns in namespaces
    )
    return _convert_deployments_to_specs(raw)


_FETCH_BY_KIND = {
    TargetKind.SERVICE: fetch_services_for_namespaces,
    TargetKind.POD: fetch_pods_for_namespaces,
    TargetKind.DEPLOYMENT: fetch_deployments_for_namespaces,
}


def fetch_targets_for_namespaces(
    namespaces: list[str],
    api: KubeGateway,
    kinds: list[TargetKind],
) -> list[PortForwardSpec]:
    """Fetch the requested kinds (with declared ports) for the picker."""
    selected = set(kinds)
    specs: list[PortForwardSpec] = []
    for kind in _FETCH_BY_KIND:
        if kind in selected:
            specs += _FETCH_BY_KIND[kind](namespaces, api)
    return specs
