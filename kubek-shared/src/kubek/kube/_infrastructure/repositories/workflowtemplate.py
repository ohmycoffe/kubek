from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import WorkflowTemplateRepository
from kubek.kube.dto import WorkflowTemplate, WorkflowTemplateList


class KubernetesWorkflowTemplateRepository(
    BaseKubernetesRepository[WorkflowTemplate, WorkflowTemplateList],
    WorkflowTemplateRepository,
):
    list_model = WorkflowTemplateList
    item_model = WorkflowTemplate

    async def _fetch_list(self, namespace: str | None = None) -> dict:
        return await self._client.get_workflowtemplates(namespace)

    async def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return await self._client.get_workflowtemplate(name=name, namespace=namespace)
