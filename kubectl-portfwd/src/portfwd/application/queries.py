import itertools
from collections.abc import Iterable

from kubek.kube import Service
from portfwd.application.ports import KubeGateway
from portfwd.domain.config import GroupSpec
from portfwd.domain.errors import NoGroupsDefinedError, UnknownGroupError
from portfwd.domain.models import NamespacedServiceNameSpec, ServicePortForwardSpec


def _convert_services_to_specs(
    services: Iterable[Service],
) -> list[ServicePortForwardSpec]:
    """Flatten Service list to (target, remote_port) specs, sorted for the picker."""
    return [
        ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(
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


def fetch_services_for_namespaces(
    namespaces: list[str], api: KubeGateway
) -> list[ServicePortForwardSpec]:
    raw = itertools.chain.from_iterable(
        api.service.list(namespace=ns) for ns in namespaces
    )
    return _convert_services_to_specs(raw)


def _resolve_group(name: str, available: list[GroupSpec]) -> GroupSpec:
    if not available:
        raise NoGroupsDefinedError("no groups defined in config file")
    for g in available:
        if g.name == name:
            return g
    names = ", ".join(sorted(g.name for g in available))
    raise UnknownGroupError(f'unknown group "{name}" (available: {names})')
