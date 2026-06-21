from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import StatefulSetRepository
from kubek.kube.dto.statefulset import StatefulSet, StatefulSetList


class KubernetesStatefulSetRepository(
    BaseKubernetesRepository[StatefulSet, StatefulSetList],
    StatefulSetRepository,
):
    list_model = StatefulSetList
    item_model = StatefulSet

    def _fetch_list(self, namespace: str | None = None) -> dict:
        return self._client.get_statefulsets(namespace)

    def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return self._client.get_statefulset(name=name, namespace=namespace)
