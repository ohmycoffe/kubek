from typing import Self

from kubek.kube._infrastructure import (
    KubernetesClient,
    KubernetesConfigMapRepository,
    KubernetesDeploymentRepository,
    KubernetesNamespaceRepository,
    KubernetesSecretRepository,
    KubernetesServiceRepository,
    KubernetesWorkflowTemplateRepository,
)
from kubek.kube.config import KubeConfig
from kubek.kube.contracts import KubeClient


class KubeFacade:
    def __init__(self, client: KubeClient):
        self.namespace = KubernetesNamespaceRepository(client)
        self.deployment = KubernetesDeploymentRepository(client)
        self.service = KubernetesServiceRepository(client)
        self.workflowtemplate = KubernetesWorkflowTemplateRepository(client)
        self.secret = KubernetesSecretRepository(client)
        self.configmap = KubernetesConfigMapRepository(client)

        self.current_config = client.current_config

    @classmethod
    def from_config(cls, config: KubeConfig | None = None) -> Self:
        return cls(KubernetesClient.from_config(config))
