from typing import Protocol

from kubek.kube.dto import WorkflowTemplate
from kubek.kube.dto.configmap import ConfigMap
from kubek.kube.dto.cronjob import CronJob
from kubek.kube.dto.daemonset import DaemonSet
from kubek.kube.dto.deployment import Deployment
from kubek.kube.dto.job import Job
from kubek.kube.dto.namespace import Namespace
from kubek.kube.dto.pod import Pod
from kubek.kube.dto.replicaset import ReplicaSet
from kubek.kube.dto.secret import Secret
from kubek.kube.dto.service import Service
from kubek.kube.dto.statefulset import StatefulSet


class ConfigMapRepository(Protocol):
    async def get(
        self, name: str, namespace: str | None = None
    ) -> ConfigMap | None: ...
    async def list(self, namespace: str | None = None) -> list[ConfigMap]: ...


class DeploymentRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[Deployment]: ...
    async def get(
        self, name: str, namespace: str | None = None
    ) -> Deployment | None: ...


class NamespaceRepository(Protocol):
    async def list(self) -> list[Namespace]: ...
    async def get(self, name: str) -> Namespace | None: ...


class PodRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[Pod]: ...
    async def get(self, name: str, namespace: str | None = None) -> Pod | None: ...


class SecretRepository(Protocol):
    async def get(self, name: str, namespace: str | None = None) -> Secret | None: ...
    async def list(self, namespace: str | None = None) -> list[Secret]: ...


class ServiceRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[Service]: ...
    async def get(self, name: str, namespace: str | None = None) -> Service | None: ...


class StatefulSetRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[StatefulSet]: ...
    async def get(
        self, name: str, namespace: str | None = None
    ) -> StatefulSet | None: ...


class DaemonSetRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[DaemonSet]: ...
    async def get(
        self, name: str, namespace: str | None = None
    ) -> DaemonSet | None: ...


class ReplicaSetRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[ReplicaSet]: ...
    async def get(
        self, name: str, namespace: str | None = None
    ) -> ReplicaSet | None: ...


class JobRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[Job]: ...
    async def get(self, name: str, namespace: str | None = None) -> Job | None: ...


class CronJobRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[CronJob]: ...
    async def get(self, name: str, namespace: str | None = None) -> CronJob | None: ...


class WorkflowTemplateRepository(Protocol):
    async def list(self, namespace: str | None = None) -> list[WorkflowTemplate]: ...
    async def get(
        self, name: str, namespace: str | None = None
    ) -> WorkflowTemplate | None: ...
