from kubek.kube import Kind

from export_dotenv.errors import UnsupportedKindError
from export_dotenv.kube import (
    ConfigMapEnvFetcher,
    CronJobEnvFetcher,
    DaemonSetEnvFetcher,
    DeploymentEnvFetcher,
    JobEnvFetcher,
    KubeGateway,
    PodEnvFetcher,
    ReplicaSetEnvFetcher,
    SecretEnvFetcher,
    StatefulSetEnvFetcher,
    WorkflowTemplateEnvFetcher,
)
from export_dotenv.kube.env_fetchers import EnvironmentValues

_FETCHERS = {
    Kind.DEPLOYMENT: DeploymentEnvFetcher,
    Kind.STATEFULSET: StatefulSetEnvFetcher,
    Kind.DAEMONSET: DaemonSetEnvFetcher,
    Kind.REPLICASET: ReplicaSetEnvFetcher,
    Kind.JOB: JobEnvFetcher,
    Kind.CRONJOB: CronJobEnvFetcher,
    Kind.WORKFLOWTEMPLATE: WorkflowTemplateEnvFetcher,
    Kind.CONFIGMAP: ConfigMapEnvFetcher,
    Kind.SECRET: SecretEnvFetcher,
    Kind.POD: PodEnvFetcher,
}


async def fetch_environment_values(
    kind: Kind, name: str, api: KubeGateway
) -> list[EnvironmentValues]:
    fetcher = _FETCHERS.get(kind)
    if not fetcher:
        raise UnsupportedKindError(f"Unsupported kind: {kind}")
    return await fetcher(api=api).fetch(name=name)
