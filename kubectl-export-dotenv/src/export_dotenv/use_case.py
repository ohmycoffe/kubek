from kubek.kube import Kind

from export_dotenv.errors import UnsupportedKindError
from export_dotenv.kube import (
    KubeGateway,
    get_configmap_envs,
    get_deployment_envs,
    get_secret_envs,
    get_workflowtemplate_envs,
)


def fetch_environment_values(kind: Kind, name: str, api: KubeGateway) -> dict[str, str]:
    if kind == Kind.DEPLOYMENT:
        return get_deployment_envs(name=name, api=api)

    if kind == Kind.WORKFLOWTEMPLATE:
        return get_workflowtemplate_envs(name=name, api=api)

    if kind == Kind.CONFIGMAP:
        return get_configmap_envs(name=name, api=api)

    if kind == Kind.SECRET:
        return get_secret_envs(name=name, api=api)

    raise UnsupportedKindError(f"Unsupported kind: {kind}")
