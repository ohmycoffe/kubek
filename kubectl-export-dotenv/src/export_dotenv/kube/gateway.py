from typing import Protocol

from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.contracts.repositories import (
    ConfigMapRepository,
    CronJobRepository,
    DaemonSetRepository,
    DeploymentRepository,
    JobRepository,
    NamespaceRepository,
    PodRepository,
    ReplicaSetRepository,
    SecretRepository,
    StatefulSetRepository,
    WorkflowTemplateRepository,
)


class KubeGateway(Protocol):
    @property
    def namespace(self) -> NamespaceRepository: ...

    @property
    def deployment(self) -> DeploymentRepository: ...

    @property
    def statefulset(self) -> StatefulSetRepository: ...

    @property
    def daemonset(self) -> DaemonSetRepository: ...

    @property
    def job(self) -> JobRepository: ...

    @property
    def cronjob(self) -> CronJobRepository: ...

    @property
    def replicaset(self) -> ReplicaSetRepository: ...

    @property
    def workflowtemplate(self) -> WorkflowTemplateRepository: ...

    @property
    def secret(self) -> SecretRepository: ...

    @property
    def configmap(self) -> ConfigMapRepository: ...

    @property
    def pod(self) -> PodRepository: ...

    @property
    def current_config(self) -> ResolvedKubeConfig: ...
