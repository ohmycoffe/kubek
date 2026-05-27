from kubek.kube import KubeFacade, Service
from kubek.net import find_free_port, get_deterministic_port, is_port_free

from portfwd.config import get_default_service
from portfwd.domain.config import PortFwdConfig
from portfwd.domain.errors import (
    AmbiguousServicePortError,
    MissingNamespaceError,
    NoServicePortsError,
    ServiceNotFoundError,
)
from portfwd.domain.models import (
    NamespacedServiceNamePlan,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)


def resolve_remote_port(service: Service) -> int:
    """Pick the single declared port of a Service or raise if ambiguous."""
    ports = service.spec.ports
    ref = f"{service.metadata.namespace}/{service.metadata.name}"
    if len(ports) == 0:
        raise NoServicePortsError(f'service "{ref}" has no ports')
    if len(ports) > 1:
        port_list = ", ".join(str(p.port) for p in ports)
        raise AmbiguousServicePortError(
            f'service "{ref}" has multiple ports ({port_list}); '
            "specify one with :port in --service"
        )
    return ports[0].port


def resolve_local_port(
    name: str,
    namespace: str,
    remote_port: int,
    config: PortFwdConfig,
) -> int:
    """Pick a local port: config default → deterministic → OS-assigned."""
    default = get_default_service(
        config=config, name=name, namespace=namespace, remote_port=remote_port
    )
    if default is not None:
        return int(default.local_port)

    deterministic = get_deterministic_port(
        service=name, namespace=namespace, service_port=remote_port
    )
    if is_port_free(deterministic):
        return deterministic
    return find_free_port()


def build_port_forward_plan(
    spec: ServicePortForwardSpec,
    config: PortFwdConfig,
    api: KubeFacade,
) -> ServicePortForwardPlan:
    """Turn a user-provided spec + cluster lookup into a concrete plan."""
    name = spec.target.name
    ns = spec.target.namespace or api.current_config.namespace
    if not ns:
        raise MissingNamespaceError(
            "namespace must be specified either in the service spec "
            "or as the current kubectl namespace"
        )

    service = api.service.get(name=name, namespace=ns)
    if not service:
        raise ServiceNotFoundError(f'service "{name}" not found in namespace "{ns}"')

    remote_port = (
        int(spec.remote_port)
        if spec.remote_port is not None
        else resolve_remote_port(service)
    )
    local_port = (
        int(spec.local_port)
        if spec.local_port is not None
        else resolve_local_port(
            name=name, namespace=ns, remote_port=remote_port, config=config
        )
    )

    return ServicePortForwardPlan(
        target=NamespacedServiceNamePlan(namespace=ns, name=name),
        remote_port=remote_port,
        local_port=local_port,
    )
