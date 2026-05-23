# contracts/client.py

from typing import Any, Protocol, Self

from kubek.kube.config import KubeConfig, ResolvedKubeConfig

KubeRawResponse = dict[str, Any]


class KubeClient(Protocol):
    @property
    def current_config(self) -> ResolvedKubeConfig: ...

    @classmethod
    def from_config(cls, config: KubeConfig | None = None) -> Self: ...

    def get_namespaces(self) -> KubeRawResponse: ...

    def get_namespace(self, name: str) -> KubeRawResponse: ...

    def get_services(self, namespace: str | None = None) -> KubeRawResponse: ...

    def get_service(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    def get_deployments(self, namespace: str | None = None) -> KubeRawResponse: ...

    def get_deployment(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    def get_secrets(self, namespace: str | None = None) -> KubeRawResponse: ...

    def get_secret(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    def get_configmaps(self, namespace: str | None = None) -> KubeRawResponse: ...

    def get_configmap(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    def get_workflowtemplates(
        self,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...

    def get_workflowtemplate(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KubeRawResponse: ...
