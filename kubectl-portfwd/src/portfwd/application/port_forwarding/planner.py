from kubek.kube import CronJob, DaemonSet, Deployment, Job, Pod, Service, StatefulSet
from kubek.net import find_free_port, get_deterministic_port, is_port_free
from portfwd.application.port_forwarding.containers import get_unique_ports
from portfwd.application.ports import KubeGateway
from portfwd.domain.errors import (
    AmbiguousCronJobPortError,
    AmbiguousDaemonSetPortError,
    AmbiguousDeploymentPortError,
    AmbiguousJobPortError,
    AmbiguousPodPortError,
    AmbiguousServicePortError,
    AmbiguousStatefulSetPortError,
    CronJobNotFoundError,
    DaemonSetNotFoundError,
    DeploymentNotFoundError,
    JobNotFoundError,
    MissingNamespaceError,
    NoCronJobPortsError,
    NoDaemonSetPortsError,
    NoDeploymentPortsError,
    NoJobPortsError,
    NoPodPortsError,
    NoServicePortsError,
    NoStatefulSetPortsError,
    PodNotFoundError,
    ServiceNotFoundError,
    StatefulSetNotFoundError,
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
    ports = get_unique_ports(pod.spec.containers)
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
    ports = get_unique_ports(deployment.spec.template.spec.containers)
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


def resolve_statefulset_remote_port(statefulset: StatefulSet) -> int:
    """Pick the single declared container port of a StatefulSet or raise if ambiguous."""
    ref = f"{statefulset.metadata.namespace}/{statefulset.metadata.name}"
    ports = get_unique_ports(statefulset.spec.template.spec.containers)
    if not ports:
        raise NoStatefulSetPortsError(
            f'statefulset "{ref}" declares no container ports; '
            "specify one with :port in the statefulset spec"
        )
    if len(ports) > 1:
        port_list = ", ".join(str(p) for p in sorted(ports))
        raise AmbiguousStatefulSetPortError(
            f'statefulset "{ref}" has multiple container ports ({port_list}); '
            "specify one with :port in the statefulset spec"
        )
    return min(ports)


def _fetch_statefulset(name: str, namespace: str, api: KubeGateway) -> StatefulSet:
    """Fetch a statefulset or raise StatefulSetNotFoundError."""
    statefulset = api.statefulset.get(name=name, namespace=namespace)
    if not statefulset:
        raise StatefulSetNotFoundError(
            f'statefulset "{name}" not found in namespace "{namespace}"'
        )
    return statefulset


def _remote_port_from_statefulset(
    name: str,
    namespace: str,
    api: KubeGateway,
    explicit_port: int | None,
) -> int:
    """Resolve the remote port for a statefulset target."""
    statefulset = _fetch_statefulset(name, namespace, api)
    if explicit_port is not None:
        return explicit_port
    return resolve_statefulset_remote_port(statefulset)


def resolve_daemonset_remote_port(daemonset: DaemonSet) -> int:
    """Pick the single declared container port of a DaemonSet or raise if ambiguous."""
    ref = f"{daemonset.metadata.namespace}/{daemonset.metadata.name}"
    ports = get_unique_ports(daemonset.spec.template.spec.containers)
    if not ports:
        raise NoDaemonSetPortsError(
            f'daemonset "{ref}" declares no container ports; '
            "specify one with :port in the daemonset spec"
        )
    if len(ports) > 1:
        port_list = ", ".join(str(p) for p in sorted(ports))
        raise AmbiguousDaemonSetPortError(
            f'daemonset "{ref}" has multiple container ports ({port_list}); '
            "specify one with :port in the daemonset spec"
        )
    return min(ports)


def _fetch_daemonset(name: str, namespace: str, api: KubeGateway) -> DaemonSet:
    """Fetch a daemonset or raise DaemonSetNotFoundError."""
    daemonset = api.daemonset.get(name=name, namespace=namespace)
    if not daemonset:
        raise DaemonSetNotFoundError(
            f'daemonset "{name}" not found in namespace "{namespace}"'
        )
    return daemonset


def _remote_port_from_daemonset(
    name: str,
    namespace: str,
    api: KubeGateway,
    explicit_port: int | None,
) -> int:
    """Resolve the remote port for a daemonset target."""
    daemonset = _fetch_daemonset(name, namespace, api)
    if explicit_port is not None:
        return explicit_port
    return resolve_daemonset_remote_port(daemonset)


def resolve_job_remote_port(job: Job) -> int:
    """Pick the single declared container port of a Job or raise if ambiguous."""
    ref = f"{job.metadata.namespace}/{job.metadata.name}"
    ports = get_unique_ports(job.spec.template.spec.containers)
    if not ports:
        raise NoJobPortsError(
            f'job "{ref}" declares no container ports; '
            "specify one with :port in the job spec"
        )
    if len(ports) > 1:
        port_list = ", ".join(str(p) for p in sorted(ports))
        raise AmbiguousJobPortError(
            f'job "{ref}" has multiple container ports ({port_list}); '
            "specify one with :port in the job spec"
        )
    return min(ports)


def _fetch_job(name: str, namespace: str, api: KubeGateway) -> Job:
    """Fetch a job or raise JobNotFoundError."""
    job = api.job.get(name=name, namespace=namespace)
    if not job:
        raise JobNotFoundError(f'job "{name}" not found in namespace "{namespace}"')
    return job


def _remote_port_from_job(
    name: str,
    namespace: str,
    api: KubeGateway,
    explicit_port: int | None,
) -> int:
    """Resolve the remote port for a job target."""
    job = _fetch_job(name, namespace, api)
    if explicit_port is not None:
        return explicit_port
    return resolve_job_remote_port(job)


def resolve_cronjob_remote_port(cronjob: CronJob) -> int:
    """Pick the single declared container port of a CronJob or raise if ambiguous."""
    ref = f"{cronjob.metadata.namespace}/{cronjob.metadata.name}"
    ports = get_unique_ports(cronjob.spec.job_template.spec.template.spec.containers)
    if not ports:
        raise NoCronJobPortsError(
            f'cronjob "{ref}" declares no container ports; '
            "specify one with :port in the cronjob spec"
        )
    if len(ports) > 1:
        port_list = ", ".join(str(p) for p in sorted(ports))
        raise AmbiguousCronJobPortError(
            f'cronjob "{ref}" has multiple container ports ({port_list}); '
            "specify one with :port in the cronjob spec"
        )
    return min(ports)


def _fetch_cronjob(name: str, namespace: str, api: KubeGateway) -> CronJob:
    """Fetch a cronjob or raise CronJobNotFoundError."""
    cronjob = api.cronjob.get(name=name, namespace=namespace)
    if not cronjob:
        raise CronJobNotFoundError(
            f'cronjob "{name}" not found in namespace "{namespace}"'
        )
    return cronjob


def _remote_port_from_cronjob(
    name: str,
    namespace: str,
    api: KubeGateway,
    explicit_port: int | None,
) -> int:
    """Resolve the remote port for a cronjob target."""
    cronjob = _fetch_cronjob(name, namespace, api)
    if explicit_port is not None:
        return explicit_port
    return resolve_cronjob_remote_port(cronjob)


_REMOTE_PORT_BY_KIND = {
    TargetKind.SERVICE: _remote_port_from_service,
    TargetKind.POD: _remote_port_from_pod,
    TargetKind.DEPLOYMENT: _remote_port_from_deployment,
    TargetKind.STATEFULSET: _remote_port_from_statefulset,
    TargetKind.DAEMONSET: _remote_port_from_daemonset,
    TargetKind.JOB: _remote_port_from_job,
    TargetKind.CRONJOB: _remote_port_from_cronjob,
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
