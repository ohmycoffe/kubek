from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import ReplicaSetRepository
from kubek.kube.dto.replicaset import ReplicaSet, ReplicaSetList


class KubernetesReplicaSetRepository(
    BaseKubernetesRepository[ReplicaSet, ReplicaSetList],
    ReplicaSetRepository,
):
    list_model = ReplicaSetList
    item_model = ReplicaSet

    async def _fetch_list(self, namespace: str | None = None) -> dict:
        return await self._client.get_replica_sets(namespace)

    async def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return await self._client.get_replica_set(name=name, namespace=namespace)
