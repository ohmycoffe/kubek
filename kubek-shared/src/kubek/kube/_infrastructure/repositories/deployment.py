from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import DeploymentRepository
from kubek.kube.dto.deployment import Deployment, DeploymentList


class KubernetesDeploymentRepository(
    BaseKubernetesRepository[Deployment, DeploymentList],
    DeploymentRepository,
):
    list_model = DeploymentList
    item_model = Deployment

    async def _fetch_list(self, namespace: str | None = None) -> dict:
        return await self._client.get_deployments(namespace)

    async def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return await self._client.get_deployment(name=name, namespace=namespace)
