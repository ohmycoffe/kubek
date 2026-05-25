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
from kubek.kube.config import KubeConfig, ResolvedKubeConfig
from kubek.kube.contracts import (
    ConfigMapRepository,
    DeploymentRepository,
    KubeClient,
    NamespaceRepository,
    SecretRepository,
    ServiceRepository,
    WorkflowTemplateRepository,
)


class KubeFacade:
    def __init__(
        self,
        current_config: ResolvedKubeConfig,
        namespace: NamespaceRepository,
        deployment: DeploymentRepository,
        service: ServiceRepository,
        workflowtemplate: WorkflowTemplateRepository,
        secret: SecretRepository,
        configmap: ConfigMapRepository,
    ):
        self.namespace = namespace
        self.deployment = deployment
        self.service = service
        self.workflowtemplate = workflowtemplate
        self.secret = secret
        self.configmap = configmap

        self.current_config = current_config

    @classmethod
    def from_config(cls, config: KubeConfig | None = None) -> Self:
        client = KubernetesClient.from_config(config)
        return cls.from_client(client)

    @classmethod
    def from_client(cls, client: KubeClient) -> Self:
        return cls(
            current_config=client.current_config,
            namespace=KubernetesNamespaceRepository(client),
            deployment=KubernetesDeploymentRepository(client),
            service=KubernetesServiceRepository(client),
            workflowtemplate=KubernetesWorkflowTemplateRepository(client),
            secret=KubernetesSecretRepository(client),
            configmap=KubernetesConfigMapRepository(client),
        )
