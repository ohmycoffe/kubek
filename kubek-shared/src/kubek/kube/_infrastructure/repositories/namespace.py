from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import NamespaceRepository
from kubek.kube.dto.namespace import Namespace, NamespaceList


class KubernetesNamespaceRepository(
    BaseKubernetesRepository[Namespace, NamespaceList],
    NamespaceRepository,
):
    list_model = NamespaceList
    item_model = Namespace

    async def _fetch_list(self) -> dict:
        return await self._client.get_namespaces()

    async def _fetch_one(self, name: str) -> dict:
        return await self._client.get_namespace(name)
