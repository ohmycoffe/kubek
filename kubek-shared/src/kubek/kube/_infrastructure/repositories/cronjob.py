from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import CronJobRepository
from kubek.kube.dto.cronjob import CronJob, CronJobList


class KubernetesCronJobRepository(
    BaseKubernetesRepository[CronJob, CronJobList],
    CronJobRepository,
):
    list_model = CronJobList
    item_model = CronJob

    def _fetch_list(self, namespace: str | None = None) -> dict:
        return self._client.get_cronjobs(namespace)

    def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return self._client.get_cronjob(name=name, namespace=namespace)
