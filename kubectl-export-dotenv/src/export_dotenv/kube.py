from __future__ import annotations

import logging
import re
from collections.abc import Callable
from functools import lru_cache

from kubek.kube import ConfigMap, Container, KubeFacade, Secret, WorkflowTemplateType

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


def get_deployment_envs(name: str, api: KubeFacade) -> dict[str, str]:
    deployment = api.deployment.get(name=name)
    if not deployment:
        raise ValueError(f"Deployment {name} not found")
    containers = deployment.spec.template.spec.containers
    if len(containers) != 1:
        raise ValueError(f"Expected 1 container, got {len(containers)}")
    container = containers[0]
    return extract_envs_from_container(api=api, container=container)


def get_workflowtemplate_envs(name: str, api: KubeFacade) -> dict[str, str]:
    workflowtemplate = api.workflowtemplate.get(name=name)
    if not workflowtemplate:
        raise ValueError(f"WorkflowTemplate {name} not found")

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


def extract_envs_from_container(
    api: KubeFacade,
    container: Container,
    fallback_keys: dict[str, str] | None = None,
) -> dict[str, str]:
    @lru_cache
    def get_secret(name: str) -> Secret | None:
        return api.secret.get(name=name)

    @lru_cache
    def get_configmap(name: str) -> ConfigMap | None:
        return api.configmap.get(name=name)

    if fallback_keys is None:
        fallback_keys = {}
    result = {}
    if container.env_from:
        for env_from in container.env_from:
            if env_from.config_map_ref:
                configmap = get_configmap(env_from.config_map_ref.name)
                if not configmap:
                    continue
                result.update(configmap.data)
            elif env_from.secret_ref:
                secret_name = env_from.secret_ref.name
                secret = get_secret(secret_name)
                if not secret:
                    continue
                result.update(secret.decoded_dict())
            else:
                raise ValueError(f"Unknown envFrom format: {env_from}")

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
