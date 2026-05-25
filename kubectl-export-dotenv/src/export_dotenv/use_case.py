from kubek.kube import Kind, KubeFacade

from export_dotenv.errors import UnsupportedKindError
from export_dotenv.kube import get_deployment_envs, get_workflowtemplate_envs


def fetch_environment_values(kind: Kind, name: str, api: KubeFacade) -> dict[str, str]:
    if kind == Kind.DEPLOYMENT:
        return get_deployment_envs(name=name, api=api)

    if kind == Kind.WORKFLOWTEMPLATE:
        return get_workflowtemplate_envs(name=name, api=api)

    raise UnsupportedKindError(f"Unsupported kind: {kind}")
