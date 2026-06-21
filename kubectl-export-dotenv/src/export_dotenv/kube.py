from __future__ import annotations

import logging
import re
from collections.abc import Callable
from functools import lru_cache
from typing import Protocol

from kubek.kube import (
    ConfigMap,
    Container,
    Secret,
    WorkflowTemplateType,
)
from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.contracts.repositories import (
    ConfigMapRepository,
    DeploymentRepository,
    NamespaceRepository,
    PodRepository,
    SecretRepository,
    StatefulSetRepository,
    WorkflowTemplateRepository,
)

from export_dotenv.errors import (
    AmbiguousResourceError,
    ResourceNotFoundError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)


class KubeGateway(Protocol):
    @property
    def namespace(self) -> NamespaceRepository: ...

    @property
    def deployment(self) -> DeploymentRepository: ...

    @property
    def statefulset(self) -> StatefulSetRepository: ...

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


def _clean_key(key: str) -> str:
    def strip_argo_inputs_param(key: str) -> str:
        match = re.match(r"^\{\{inputs\.parameters\.(?P<param_name>\w+)\}\}$", key)
        return match.group("param_name") if match else key

    cleanups: list[Callable[[str], str]] = [
        strip_argo_inputs_param,
    ]

    for cleanup in cleanups:
        key = cleanup(key)
    return key


def get_deployment_envs(name: str, api: KubeGateway) -> dict[str, str]:
    ns = api.current_config.namespace
    deployment = api.deployment.get(name=name, namespace=ns)
    if not deployment:
        raise ResourceNotFoundError(f"Deployment {name} not found in namespace {ns}")
    containers = deployment.spec.template.spec.containers
    if len(containers) != 1:
        raise AmbiguousResourceError(
            f"Deployment {name} in namespace {ns} has {len(containers)} containers, expected exactly 1. "
            "This tool only supports exporting env vars for deployments with a single container."
        )
    container = containers[0]
    return extract_envs_from_container(api=api, container=container)


def get_pod_envs(name: str, api: KubeGateway) -> dict[str, str]:
    ns = api.current_config.namespace
    pod = api.pod.get(name=name, namespace=ns)
    if not pod:
        raise ResourceNotFoundError(f"Pod {name} not found in namespace {ns}")
    containers = pod.spec.containers
    if len(containers) != 1:
        raise AmbiguousResourceError(
            f"Pod {name} in namespace {ns} has {len(containers)} containers, expected exactly 1. "
            "This tool only supports exporting env vars for pods with a single container."
        )
    container = containers[0]
    return extract_envs_from_container(api=api, container=container)


def get_statefulset_envs(name: str, api: KubeGateway) -> dict[str, str]:
    ns = api.current_config.namespace
    statefulset = api.statefulset.get(name=name, namespace=ns)
    if not statefulset:
        raise ResourceNotFoundError(f"StatefulSet {name} not found in namespace {ns}")
    containers = statefulset.spec.template.spec.containers
    if len(containers) != 1:
        raise AmbiguousResourceError(
            f"StatefulSet {name} in namespace {ns} has {len(containers)} containers, expected exactly 1. "
            "This tool only supports exporting env vars for statefulsets with a single container."
        )
    container = containers[0]
    return extract_envs_from_container(api=api, container=container)


def get_workflowtemplate_envs(name: str, api: KubeGateway) -> dict[str, str]:
    ns = api.current_config.namespace
    workflowtemplate = api.workflowtemplate.get(name=name, namespace=ns)
    if not workflowtemplate:
        raise ResourceNotFoundError(
            f"WorkflowTemplate {name} not found in namespace {ns}"
        )

    all_envs = {}
    for template in workflowtemplate.spec.templates:
        if template.kind != WorkflowTemplateType.CONTAINER:
            # keep only container templates
            continue
        fallback_keys = {}
        if template.inputs and template.inputs.parameters:
            fallback_keys |= {
                p.name: p.default
                for p in template.inputs.parameters
                if p.default is not None
            }

        template_envs = extract_envs_from_container(
            api=api, container=template.container, fallback_keys=fallback_keys
        )
        all_envs.update(template_envs)

    return all_envs


def get_configmap_envs(name: str, api: KubeGateway) -> dict[str, str]:
    ns = api.current_config.namespace
    configmap = api.configmap.get(name=name, namespace=ns)
    if not configmap:
        raise ResourceNotFoundError(f"ConfigMap {name} not found in namespace {ns}")
    return configmap.data


def get_secret_envs(name: str, api: KubeGateway) -> dict[str, str]:
    ns = api.current_config.namespace
    secret = api.secret.get(name=name, namespace=ns)
    if not secret:
        raise ResourceNotFoundError(f"Secret {name} not found in namespace {ns}")
    return secret.decoded_dict()


def extract_envs_from_container(
    api: KubeGateway,
    container: Container,
    fallback_keys: dict[str, str] | None = None,
) -> dict[str, str]:
    @lru_cache
    def get_secret(name: str) -> Secret | None:
        return api.secret.get(name=name, namespace=api.current_config.namespace)

    @lru_cache
    def get_configmap(name: str) -> ConfigMap | None:
        return api.configmap.get(name=name, namespace=api.current_config.namespace)

    if fallback_keys is None:
        fallback_keys = {}
    result = {}
    if container.env_from:
        for env_from in container.env_from:
            if env_from.config_map_ref:
                configmap = get_configmap(env_from.config_map_ref.name)
                if not configmap:
                    cfg_map_name = env_from.config_map_ref.name
                    logger.warning(f"ConfigMap {cfg_map_name} not found, skipping.")
                    continue
                result.update(configmap.data)
            elif env_from.secret_ref:
                secret_name = env_from.secret_ref.name
                secret = get_secret(secret_name)
                if not secret:
                    logger.warning(f"Secret {secret_name} not found, skipping.")
                    continue
                result.update(secret.decoded_dict())
            else:
                raise UnsupportedFormatError(f"Unknown envFrom format: {env_from}")

    if container.env:
        for env in container.env:
            name = env.name
            if env.value:
                value = env.value
                result[name] = value
            elif env.value_from:
                value_from = env.value_from
                if value_from.config_map_key_ref:
                    configmap = get_configmap(value_from.config_map_key_ref.name)
                    if configmap is None:
                        cfg_map_name = value_from.config_map_key_ref.name
                        logger.warning(f"ConfigMap {cfg_map_name} not found, skipping.")
                        continue
                    key = value_from.config_map_key_ref.key
                    if key not in configmap.data:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in configmap.data:
                        logger.warning(
                            f"{name} won't be set: key {key} not found in ConfigMap {value_from.config_map_key_ref.name}"
                        )
                        value = ""
                    else:
                        value = configmap.data[key]
                    result[name] = value
                elif value_from.secret_key_ref:
                    secret_name = value_from.secret_key_ref.name
                    secret = get_secret(secret_name)
                    if secret is None:
                        logger.warning(f"Secret {secret_name} not found, skipping.")
                        continue
                    key = value_from.secret_key_ref.key
                    if key not in secret.data:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in secret.data:
                        logger.warning(
                            f"{name} won't be set: key {key} not found in Secret {secret_name}"
                        )
                        value = ""
                    else:
                        value = secret.decoded(key)
                    result[name] = value
                else:
                    logger.warning(
                        f"Unknown valueFrom format: {value_from} for {name} ({env})"
                    )
            else:
                logger.warning(f"Unknown env format: {env}")
    return result
