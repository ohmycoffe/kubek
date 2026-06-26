from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import DaemonSetRepository
from kubek.kube.dto.daemonset import DaemonSet, DaemonSetList


class KubernetesDaemonSetRepository(
    BaseKubernetesRepository[DaemonSet, DaemonSetList],
    DaemonSetRepository,
):
    list_model = DaemonSetList
    item_model = DaemonSet

    async def _fetch_list(self, namespace: str | None = None) -> dict:
        return await self._client.get_daemonsets(namespace)

    async def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return await self._client.get_daemonset(name=name, namespace=namespace)
