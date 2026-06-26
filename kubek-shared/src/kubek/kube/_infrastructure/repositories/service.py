from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import ServiceRepository
from kubek.kube.dto.service import Service, ServiceList


class KubernetesServiceRepository(
    BaseKubernetesRepository[Service, ServiceList], ServiceRepository
):
    list_model = ServiceList
    item_model = Service

    async def _fetch_list(self, namespace: str | None = None) -> dict:
        return await self._client.get_services(namespace)

    async def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return await self._client.get_service(name=name, namespace=namespace)
