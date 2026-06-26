from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import ConfigMapRepository
from kubek.kube.dto.configmap import ConfigMap, ConfigMapList


class KubernetesConfigMapRepository(
    BaseKubernetesRepository[ConfigMap, ConfigMapList],
    ConfigMapRepository,
):
    list_model = ConfigMapList
    item_model = ConfigMap

    async def _fetch_list(self, namespace: str | None = None) -> dict:
        return await self._client.get_configmaps(namespace)

    async def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return await self._client.get_configmap(name=name, namespace=namespace)
