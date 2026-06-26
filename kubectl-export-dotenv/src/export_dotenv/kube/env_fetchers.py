from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from kubek.kube import Container, WorkflowTemplateType
from kubek.kube.dto.kind import Kind

from export_dotenv.errors import ResourceNotFoundError
from export_dotenv.kube.env_resolver import (
    extract_envs_from_container,
)
from export_dotenv.kube.gateway import KubeGateway


@dataclass(frozen=True)
class EnvironmentValues:
    name: str
    values: dict[str, str]


class KubeResourceEnvFetcher(ABC):
    kind: Kind

    def __init__(self, api: KubeGateway) -> None:
        self.api = api

    @abstractmethod
    async def fetch(self, name: str) -> list[EnvironmentValues]: ...


class BaseEnvFetcher(KubeResourceEnvFetcher):
    async def fetch(self, name: str) -> list[EnvironmentValues]:
        namespace = self.api.current_config.namespace

        resource = await self._get_resource(name=name, namespace=namespace)
        if resource is None:
            raise ResourceNotFoundError(
                f"{self.kind.value} {name} not found in namespace {namespace}"
            )

        containers = self._get_containers(resource)
        if not containers:
            raise ResourceNotFoundError(
                f"{self.kind.value} {name} in namespace {namespace} has no containers"
            )

        return await self._extract_envs_from_containers(containers=containers)

    async def _extract_envs_from_containers(
        self, containers: list[Container]
    ) -> list[EnvironmentValues]:
        res = []
        for container in containers:
            envs = await extract_envs_from_container(api=self.api, container=container)
            res.append(EnvironmentValues(name=container.name, values=envs))
        return res

    @abstractmethod
    async def _get_resource(self, name: str, namespace: str) -> Any | None: ...

    @abstractmethod
    def _get_containers(self, resource: Any) -> list[Container]: ...


class DeploymentEnvFetcher(BaseEnvFetcher):
    kind = Kind.DEPLOYMENT

    async def _get_resource(self, name: str, namespace: str) -> Any | None:
        return await self.api.deployment.get(name=name, namespace=namespace)

    def _get_containers(self, resource: Any) -> list[Container]:
        return resource.spec.template.spec.containers


class StatefulSetEnvFetcher(BaseEnvFetcher):
    kind = Kind.STATEFULSET

    async def _get_resource(self, name: str, namespace: str) -> Any | None:
        return await self.api.statefulset.get(name=name, namespace=namespace)

    def _get_containers(self, resource: Any) -> list[Container]:
        return resource.spec.template.spec.containers


class DaemonSetEnvFetcher(BaseEnvFetcher):
    kind = Kind.DAEMONSET

    async def _get_resource(self, name: str, namespace: str) -> Any | None:
        return await self.api.daemonset.get(name=name, namespace=namespace)

    def _get_containers(self, resource: Any) -> list[Container]:
        return resource.spec.template.spec.containers


class ReplicaSetEnvFetcher(BaseEnvFetcher):
    kind = Kind.REPLICASET

    async def _get_resource(self, name: str, namespace: str) -> Any | None:
        return await self.api.replicaset.get(name=name, namespace=namespace)

    def _get_containers(self, resource: Any) -> list[Container]:
        return resource.spec.template.spec.containers


class JobEnvFetcher(BaseEnvFetcher):
    kind = Kind.JOB

    async def _get_resource(self, name: str, namespace: str) -> Any | None:
        return await self.api.job.get(name=name, namespace=namespace)

    def _get_containers(self, resource: Any) -> list[Container]:
        return resource.spec.template.spec.containers


class CronJobEnvFetcher(BaseEnvFetcher):
    kind = Kind.CRONJOB

    async def _get_resource(self, name: str, namespace: str) -> Any | None:
        return await self.api.cronjob.get(name=name, namespace=namespace)

    def _get_containers(self, resource: Any) -> list[Container]:
        return resource.spec.job_template.spec.template.spec.containers


class PodEnvFetcher(BaseEnvFetcher):
    kind = Kind.POD

    async def _get_resource(self, name: str, namespace: str) -> Any | None:
        return await self.api.pod.get(name=name, namespace=namespace)

    def _get_containers(self, resource: Any) -> list[Container]:
        return resource.spec.containers


class SecretEnvFetcher(KubeResourceEnvFetcher):
    kind = Kind.SECRET

    async def fetch(self, name: str) -> list[EnvironmentValues]:
        ns = self.api.current_config.namespace
        secret = await self.api.secret.get(name=name, namespace=ns)
        if not secret:
            raise ResourceNotFoundError(f"Secret {name} not found in namespace {ns}")
        return [EnvironmentValues(name=name, values=secret.decoded_dict())]


class ConfigMapEnvFetcher(KubeResourceEnvFetcher):
    kind = Kind.CONFIGMAP

    async def fetch(self, name: str) -> list[EnvironmentValues]:
        ns = self.api.current_config.namespace
        configmap = await self.api.configmap.get(name=name, namespace=ns)
        if not configmap:
            raise ResourceNotFoundError(f"ConfigMap {name} not found in namespace {ns}")
        return [EnvironmentValues(name=name, values=configmap.data)]


class WorkflowTemplateEnvFetcher(KubeResourceEnvFetcher):
    kind = Kind.WORKFLOWTEMPLATE

    async def fetch(self, name: str) -> list[EnvironmentValues]:
        ns = self.api.current_config.namespace
        workflowtemplate = await self.api.workflowtemplate.get(name=name, namespace=ns)
        if not workflowtemplate:
            raise ResourceNotFoundError(
                f"WorkflowTemplate {name} not found in namespace {ns}"
            )

        all_envs = []
        for template in workflowtemplate.spec.templates:
            if template.kind != WorkflowTemplateType.CONTAINER:
                continue
            fallback_keys = {}
            if template.inputs and template.inputs.parameters:
                fallback_keys |= {
                    p.name: p.default
                    for p in template.inputs.parameters
                    if p.default is not None
                }

            template_envs = await extract_envs_from_container(
                api=self.api, container=template.container, fallback_keys=fallback_keys
            )
            all_envs.append(EnvironmentValues(name=template.name, values=template_envs))

        return all_envs
