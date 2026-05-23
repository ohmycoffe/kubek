from kubek.kube import KubeFacade, Service
from kubek.net import find_free_port, get_deterministic_port, is_port_free

from portfwd.config import (
    PortFwdConfig,
    get_default_service,
)
from portfwd.errors import (
    KubernetesError,
)
from portfwd.models import (
    NamespacedServiceName,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)


def resolve_remote_port(service: Service) -> int:
    # If there are multiple ports, we cannot guess which one to use
    if len(service.spec.ports) > 1:
        ports = ", ".join(str(p.port) for p in service.spec.ports)
        raise KubernetesError(
            f'error: service "{service.metadata.namespace}/{service.metadata.name}" has multiple ports '
            f"({ports}); specify one with :port in --service"
        )
    if len(service.spec.ports) == 0:
        raise KubernetesError(
            f'error: service "{service.metadata.namespace}/{service.metadata.name}" has no ports'
        )
    # If there is exactly one port, we can use it
    return service.spec.ports[0].port


def resolve_local_port(
    name: str,
    namespace: str,
    remote_port: int,
    config: PortFwdConfig,
) -> int:
    # If there is a default config for this service with a local port specified, use it
    default_service = get_default_service(
        config=config,
        name=name,
        namespace=namespace,
        remote_port=remote_port,
    )
    if default_service is not None:
        return int(default_service.local_port)

    # otherwise, we need to find a free local port to use
    deterministic_port = get_deterministic_port(
        service=name,
        namespace=namespace,
        service_port=remote_port,
    )
    if is_port_free(deterministic_port):
        return deterministic_port

    return find_free_port()


def build_port_forward_plan(
    spec: ServicePortForwardSpec,
    config: PortFwdConfig,
    api: KubeFacade,
) -> ServicePortForwardPlan:
    name = spec.target.name
    ns = spec.target.namespace or api.current_config.namespace
    if not ns:
        raise ValueError(
            "error: namespace must be specified either in the service spec or as the current kubectl namespace"
        )

    service = api.service.get(name=name, namespace=ns)
    if not service:
        raise KubernetesError(f'error: services "{name}" not found in namespace "{ns}"')

    # Assign a remote port
    # If remote port is explicitly specified in the spec, use it
    if spec.remote_port is not None:
        remote_port = int(spec.remote_port)
    else:
        remote_port = resolve_remote_port(service)

    # Assign a local port
    # If local port is explicitly specified in the spec, use it
    if spec.local_port is not None:
        local_port = int(spec.local_port)
    else:
        local_port = resolve_local_port(
            name=name, namespace=ns, remote_port=remote_port, config=config
        )

    return ServicePortForwardPlan(
        target=NamespacedServiceName(namespace=ns, name=name),
        remote_port=remote_port,
        local_port=local_port,
    )
