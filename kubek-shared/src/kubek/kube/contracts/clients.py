# contracts/client.py

from typing import Any, Protocol

from kubek.kube.config import ResolvedKubeConfig

KubeRawResponse = dict[str, Any]


class KubeClient(Protocol):
    @property
    def current_config(self) -> ResolvedKubeConfig: ...

    async def get_namespaces(self) -> KubeRawResponse: ...

    async def get_namespace(self, name: str) -> KubeRawResponse: ...

    async def get_services(self, namespace: str | None = None) -> KubeRawResponse: ...

    async def get_service(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_pods(self, namespace: str | None = None) -> KubeRawResponse: ...

    async def get_pod(
        self, name: str, namespace: str | None = None
    ) -> KubeRawResponse: ...

    async def get_deployments(
        self, namespace: str | None = None
    ) -> KubeRawResponse: ...

    async def get_deployment(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_statefulsets(
        self, namespace: str | None = None
    ) -> KubeRawResponse: ...

    async def get_statefulset(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_daemonsets(self, namespace: str | None = None) -> KubeRawResponse: ...

    async def get_daemonset(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_replica_sets(
        self, namespace: str | None = None
    ) -> KubeRawResponse: ...

    async def get_replica_set(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_jobs(self, namespace: str | None = None) -> KubeRawResponse: ...

    async def get_job(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_cronjobs(self, namespace: str | None = None) -> KubeRawResponse: ...

    async def get_cronjob(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_secrets(self, namespace: str | None = None) -> KubeRawResponse: ...

    async def get_secret(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_configmaps(self, namespace: str | None = None) -> KubeRawResponse: ...

    async def get_configmap(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_workflowtemplates(
        self,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    async def get_workflowtemplate(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...
