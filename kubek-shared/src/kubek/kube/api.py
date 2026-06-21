from typing import Self

from kubek.kube._infrastructure import (
    KubernetesClient,
    KubernetesConfigMapRepository,
    KubernetesCronJobRepository,
    KubernetesDaemonSetRepository,
    KubernetesDeploymentRepository,
    KubernetesJobRepository,
    KubernetesNamespaceRepository,
    KubernetesPodRepository,
    KubernetesSecretRepository,
    KubernetesServiceRepository,
    KubernetesStatefulSetRepository,
    KubernetesWorkflowTemplateRepository,
)
from kubek.kube.config import KubeConfig, ResolvedKubeConfig
from kubek.kube.contracts import (
    KubeClient,
)


class KubeFacade:
    def __init__(
        self,
        current_config: ResolvedKubeConfig,
        namespace: KubernetesNamespaceRepository,
        deployment: KubernetesDeploymentRepository,
        statefulset: KubernetesStatefulSetRepository,
        daemonset: KubernetesDaemonSetRepository,
        job: KubernetesJobRepository,
        cronjob: KubernetesCronJobRepository,
        service: KubernetesServiceRepository,
        pod: KubernetesPodRepository,
        workflowtemplate: KubernetesWorkflowTemplateRepository,
        secret: KubernetesSecretRepository,
        configmap: KubernetesConfigMapRepository,
    ):
        self.namespace = namespace
        self.deployment = deployment
        self.statefulset = statefulset
        self.daemonset = daemonset
        self.job = job
        self.cronjob = cronjob
        self.service = service
        self.pod = pod
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
            statefulset=KubernetesStatefulSetRepository(client),
            daemonset=KubernetesDaemonSetRepository(client),
            job=KubernetesJobRepository(client),
            cronjob=KubernetesCronJobRepository(client),
            service=KubernetesServiceRepository(client),
            pod=KubernetesPodRepository(client),
            workflowtemplate=KubernetesWorkflowTemplateRepository(client),
            secret=KubernetesSecretRepository(client),
            configmap=KubernetesConfigMapRepository(client),
        )
