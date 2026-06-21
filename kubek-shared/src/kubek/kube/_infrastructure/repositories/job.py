from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import JobRepository
from kubek.kube.dto.job import Job, JobList


class KubernetesJobRepository(
    BaseKubernetesRepository[Job, JobList],
    JobRepository,
):
    list_model = JobList
    item_model = Job

    def _fetch_list(self, namespace: str | None = None) -> dict:
        return self._client.get_jobs(namespace)

    def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return self._client.get_job(name=name, namespace=namespace)
