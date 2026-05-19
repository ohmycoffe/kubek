from __future__ import annotations

import logging
import re
from collections.abc import Callable
from functools import lru_cache

from kubek.kube.client import KubectlWrapper
from kubek.kube.schemas.configmap import ConfigMap
from kubek.kube.schemas.container import Container
from kubek.kube.schemas.secret import Secret
from kubek.kube.schemas.workflowtemplate import TemplateType

logger = logging.getLogger(__name__)


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


def get_deployment_envs(name: str, kubectl: KubectlWrapper) -> dict[str, str]:
    deployment = kubectl.get_deployment(name=name)
    containers = deployment.spec.template.spec.containers
    if len(containers) != 1:
        raise ValueError(f"Expected 1 container, got {len(containers)}")
    container = containers[0]
    return extract_envs_from_container(kubectl=kubectl, container=container)


def get_workflowtemplate_envs(name: str, kubectl: KubectlWrapper) -> dict[str, str]:
    workflowtemplate = kubectl.get_workflowtemplate(name=name)

    all_envs = {}
    for template in workflowtemplate.spec.templates:
        if template.kind != TemplateType.CONTAINER:
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
            kubectl=kubectl, container=template.container, fallback_keys=fallback_keys
        )
        all_envs.update(template_envs)

    return all_envs


def extract_envs_from_container(
    kubectl: KubectlWrapper,
    container: Container,
    fallback_keys: dict[str, str] | None = None,
) -> dict[str, str]:
    @lru_cache
    def get_secret(name: str) -> Secret:
        return kubectl.get_secret(name=name)

    @lru_cache
    def get_configmap(name: str) -> ConfigMap:
        return kubectl.get_configmap(name=name)

    if fallback_keys is None:
        fallback_keys = {}
    result = {}
    if container.envFrom:
        for env_from in container.envFrom:
            if env_from.configMapRef:
                configmap = get_configmap(env_from.configMapRef.name)
                result.update(configmap.data)
            elif env_from.secretRef:
                secret_name = env_from.secretRef.name
                secret = get_secret(secret_name)
                result.update(secret.decoded_data)
            else:
                raise ValueError(f"Unknown envFrom format: {env_from}")

    if container.env:
        for env in container.env:
            name = env.name
            if env.value:
                value = env.value
                result[name] = value
            elif env.valueFrom:
                value_from = env.valueFrom
                if value_from.configMapKeyRef:
                    configmap = get_configmap(value_from.configMapKeyRef.name)
                    key = value_from.configMapKeyRef.key
                    if key not in configmap.data:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in configmap.data:
                        logger.warning(
                            f"{name} won't be set: key {key} not found in ConfigMap {value_from.configMapKeyRef.name}"
                        )
                        value = ""
                    else:
                        value = configmap.data[key]
                    result[name] = value
                elif value_from.secretKeyRef:
                    secret_name = value_from.secretKeyRef.name
                    secret = get_secret(secret_name)
                    key = value_from.secretKeyRef.key
                    if key not in secret.data:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in secret.data:
                        logger.warning(
                            f"{name} won't be set: key {key} not found in Secret {secret_name}"
                        )
                        value = ""
                    else:
                        value = secret.decoded_data[key]
                    result[name] = value
                else:
                    logger.warning(
                        f"Unknown valueFrom format: {value_from} for {name} ({env})"
                    )
            else:
                logger.warning(f"Unknown env format: {env}")
    return result
