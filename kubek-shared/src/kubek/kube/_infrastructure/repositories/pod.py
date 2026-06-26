from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import PodRepository
from kubek.kube.dto.pod import Pod, PodList


class KubernetesPodRepository(BaseKubernetesRepository[Pod, PodList], PodRepository):
    list_model = PodList
    item_model = Pod

    async def _fetch_list(self, namespace: str | None = None) -> dict:
        return await self._client.get_pods(namespace)

    async def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return await self._client.get_pod(name=name, namespace=namespace)
