from kubek.kube import Deployment, Pod, Service
from kubek.net import find_free_port, get_deterministic_port, is_port_free
from portfwd.application.port_forwarding.deployment import (
    container_ports as deployment_container_ports,
)
from portfwd.application.port_forwarding.pod import (
    container_ports as pod_container_ports,
)
from portfwd.application.ports import KubeGateway
from portfwd.domain.errors import (
    AmbiguousDeploymentPortError,
    AmbiguousPodPortError,
    AmbiguousServicePortError,
    DeploymentNotFoundError,
    MissingNamespaceError,
    NoDeploymentPortsError,
    NoPodPortsError,
    NoServicePortsError,
    PodNotFoundError,
    ServiceNotFoundError,
)
from portfwd.domain.models import (
    PortForwardPlan,
    PortForwardSpec,
    ResolvedTargetRef,
    TargetKind,
)


def resolve_service_remote_port(service: Service) -> int:
    """Pick the single declared port of a Service or raise if ambiguous."""
    ports = service.spec.ports
    ref = f"{service.metadata.namespace}/{service.metadata.name}"
    if len(ports) == 0:
        raise NoServicePortsError(f'service "{ref}" has no ports')
    if len(ports) > 1:
        port_list = ", ".join(str(p.port) for p in ports)
        raise AmbiguousServicePortError(
            f'service "{ref}" has multiple ports ({port_list}); '
            "specify one with :port in the service spec"
        )
    return ports[0].port


def resolve_pod_remote_port(pod: Pod) -> int:
    """Pick the single declared container port of a Pod or raise if ambiguous."""
    ref = f"{pod.metadata.namespace}/{pod.metadata.name}"
    ports = pod_container_ports(pod)
    if not ports:
        raise NoPodPortsError(
            f'pod "{ref}" declares no container ports; '
            "specify one with :port in the pod spec"
        )
    if len(ports) > 1:
        port_list = ", ".join(str(p) for p in sorted(ports))
        raise AmbiguousPodPortError(
            f'pod "{ref}" has multiple container ports ({port_list}); '
            "specify one with :port in the pod spec"
        )
    return min(ports)


def resolve_local_port(
    name: str,
    namespace: str,
    remote_port: int,
) -> int:
    """Pick a local port: deterministic when free, otherwise OS-assigned."""
    deterministic = get_deterministic_port(
        name=name, namespace=namespace, service_port=remote_port
    )
    if is_port_free(deterministic):
        return deterministic
    return find_free_port()


def _fetch_service(name: str, namespace: str, api: KubeGateway) -> Service:
    service = api.service.get(name=name, namespace=namespace)
    if not service:
        raise ServiceNotFoundError(
            f'service "{name}" not found in namespace "{namespace}"'
        )
    return service


def _fetch_pod(name: str, namespace: str, api: KubeGateway) -> Pod:
    pod = api.pod.get(name=name, namespace=namespace)
    if not pod:
        raise PodNotFoundError(f'pod "{name}" not found in namespace "{namespace}"')
    return pod


def _remote_port_from_service(
    name: str,
    namespace: str,
    api: KubeGateway,
    explicit_port: int | None,
) -> int:
    service = _fetch_service(name, namespace, api)
    if explicit_port is not None:
        return explicit_port
    return resolve_service_remote_port(service)


def _remote_port_from_pod(
    name: str,
    namespace: str,
    api: KubeGateway,
    explicit_port: int | None,
) -> int:
    """Resolve the remote port for a pod target."""
    pod = _fetch_pod(name, namespace, api)
    if explicit_port is not None:
        return explicit_port
    return resolve_pod_remote_port(pod)


def resolve_deployment_remote_port(deployment: Deployment) -> int:
    """Pick the single declared container port of a Deployment or raise if ambiguous."""
    ref = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
    ports = deployment_container_ports(deployment)
    if not ports:
        raise NoDeploymentPortsError(
            f'deployment "{ref}" declares no container ports; '
            "specify one with :port in the deployment spec"
        )
    if len(ports) > 1:
        port_list = ", ".join(str(p) for p in sorted(ports))
        raise AmbiguousDeploymentPortError(
            f'deployment "{ref}" has multiple container ports ({port_list}); '
            "specify one with :port in the deployment spec"
        )
    return min(ports)


def _fetch_deployment(name: str, namespace: str, api: KubeGateway) -> Deployment:
    """Fetch a deployment or raise DeploymentNotFoundError."""
    deployment = api.deployment.get(name=name, namespace=namespace)
    if not deployment:
        raise DeploymentNotFoundError(
            f'deployment "{name}" not found in namespace "{namespace}"'
        )
    return deployment


def _remote_port_from_deployment(
    name: str,
    namespace: str,
    api: KubeGateway,
    explicit_port: int | None,
) -> int:
    """Resolve the remote port for a deployment target."""
    deployment = _fetch_deployment(name, namespace, api)
    if explicit_port is not None:
        return explicit_port
    return resolve_deployment_remote_port(deployment)


_REMOTE_PORT_BY_KIND = {
    TargetKind.SERVICE: _remote_port_from_service,
    TargetKind.POD: _remote_port_from_pod,
    TargetKind.DEPLOYMENT: _remote_port_from_deployment,
}


def _resolve_remote_port(
    spec: PortForwardSpec,
    name: str,
    namespace: str,
    api: KubeGateway,
) -> int:
    """Resolve the remote port, validating the target exists either way.

    The target is always fetched so a missing service/pod fails fast, even when
    the remote port is given explicitly.
    """
    resolver = _REMOTE_PORT_BY_KIND[spec.target.kind]
    return resolver(name, namespace, api, spec.remote_port)


def build_port_forward_plan(
    spec: PortForwardSpec,
    api: KubeGateway,
) -> PortForwardPlan:
    """Turn a user-provided spec + cluster lookup into a concrete plan."""
    name = spec.target.name
    ns = spec.target.namespace or api.current_config.namespace
    if not ns:
        raise MissingNamespaceError(
            "namespace must be specified either in the target spec "
            "or as the current kubectl namespace"
        )

    remote_port = _resolve_remote_port(spec=spec, name=name, namespace=ns, api=api)
    local_port = (
        spec.local_port
        if spec.local_port is not None
        else resolve_local_port(name=name, namespace=ns, remote_port=remote_port)
    )

    return PortForwardPlan(
        target=ResolvedTargetRef(kind=spec.target.kind, namespace=ns, name=name),
        remote_port=remote_port,
        local_port=local_port,
    )
