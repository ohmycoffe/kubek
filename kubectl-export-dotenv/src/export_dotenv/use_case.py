from kubek.kube import Kind

from export_dotenv.errors import UnsupportedKindError
from export_dotenv.kube import (
    KubeGateway,
    get_configmap_envs,
    get_cronjob_envs,
    get_daemonset_envs,
    get_deployment_envs,
    get_job_envs,
    get_pod_envs,
    get_replicaset_envs,
    get_secret_envs,
    get_statefulset_envs,
    get_workflowtemplate_envs,
)


def fetch_environment_values(kind: Kind, name: str, api: KubeGateway) -> dict[str, str]:
    if kind == Kind.DEPLOYMENT:
        return get_deployment_envs(name=name, api=api)

    if kind == Kind.STATEFULSET:
        return get_statefulset_envs(name=name, api=api)

    if kind == Kind.DAEMONSET:
        return get_daemonset_envs(name=name, api=api)

    if kind == Kind.REPLICASET:
        return get_replicaset_envs(name=name, api=api)

    if kind == Kind.JOB:
        return get_job_envs(name=name, api=api)

    if kind == Kind.CRONJOB:
        return get_cronjob_envs(name=name, api=api)

    if kind == Kind.WORKFLOWTEMPLATE:
        return get_workflowtemplate_envs(name=name, api=api)

    if kind == Kind.CONFIGMAP:
        return get_configmap_envs(name=name, api=api)

    if kind == Kind.SECRET:
        return get_secret_envs(name=name, api=api)

    if kind == Kind.POD:
        return get_pod_envs(name=name, api=api)

    raise UnsupportedKindError(f"Unsupported kind: {kind}")
