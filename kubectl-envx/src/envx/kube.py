from __future__ import annotations

import json
import logging
import re
import subprocess
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from envx.utils import decode

logger = logging.getLogger(__name__)


def call_subprocess(cmd: list[str]) -> str:
    logger.debug("%s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def get_current_namespace() -> str:
    """Get the active namespace from kubeconfig, falling back to 'default'."""
    result = call_subprocess(
        ["kubectl", "config", "view", "--minify", "-o", "jsonpath={..namespace}"]
    )
    return result.strip() or "default"


@lru_cache
def get_secret(namespace: str, name: str) -> dict[str, Any]:
    cmd = ["kubectl", "get", "secret", name, "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    secret = json.loads(result)
    return secret


@lru_cache
def get_configmap(namespace: str, name: str) -> dict[str, Any]:
    cmd = ["kubectl", "get", "configmap", name, "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    configmap = json.loads(result)
    return configmap


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


def get_available_deployments(namespace: str) -> list[str]:
    cmd = ["kubectl", "get", "deployment", "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    data = json.loads(result)
    return [el["metadata"]["name"] for el in data["items"]]


def get_deployment_envs(namespace: str, name: str) -> dict[str, str]:
    cmd = ["kubectl", "get", "deployment", name, "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    deployment = json.loads(result)
    containers = deployment["spec"]["template"]["spec"]["containers"]
    if len(containers) != 1:
        raise ValueError(f"Expected 1 container, got {len(containers)}")
    return extract_envs_from_container(namespace=namespace, container=containers[0])


def get_available_workflowtemplates(namespace: str) -> list[str]:
    cmd = ["kubectl", "get", "workflowtemplate", "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    data = json.loads(result)
    return [el["metadata"]["name"] for el in data["items"]]


def get_workflowtemplate_envs(namespace: str, name: str) -> dict[str, str]:
    cmd = ["kubectl", "get", "workflowtemplate", name, "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    workflow = json.loads(result)
    envs = {}
    for template in workflow["spec"]["templates"]:
        if "container" not in template:
            continue
        fallback_keys = {
            p["name"]: p["default"]
            for p in template.get("inputs", {}).get("parameters", [])
            if "default" in p
        }
        envs.update(
            extract_envs_from_container(
                namespace, template["container"], fallback_keys=fallback_keys
            )
        )
    return envs


def extract_envs_from_container(
    namespace: str,
    container: dict[str, Any],
    fallback_keys: dict[str, str] | None = None,
) -> dict[str, str]:
    if fallback_keys is None:
        fallback_keys = {}
    result = {}
    if "envFrom" in container:
        for env_from in container["envFrom"]:
            if "configMapRef" in env_from:
                configmap = get_configmap(namespace, env_from["configMapRef"]["name"])
                result.update(configmap["data"])
            elif "secretRef" in env_from:
                secret_name = env_from["secretRef"]["name"]
                secret = get_secret(namespace, secret_name)
                encoded = {k: decode(v) for k, v in secret["data"].items()}
                result.update(encoded)
            else:
                raise ValueError(f"Unknown envFrom format: {env_from}")

    if "env" in container:
        for env in container["env"]:
            name = env["name"]
            if "value" in env:
                value = env["value"]
                result[name] = value
            elif "valueFrom" in env:
                value_from = env["valueFrom"]
                if "configMapKeyRef" in value_from:
                    configmap = get_configmap(
                        namespace, value_from["configMapKeyRef"]["name"]
                    )
                    key = value_from["configMapKeyRef"]["key"]
                    if key not in configmap["data"]:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in configmap["data"]:
                        logger.warning(
                            f"{name} won't be set: key {key} not found in ConfigMap {value_from['configMapKeyRef']['name']}"
                        )
                        value = ""
                    else:
                        value = configmap["data"][key]
                    result[name] = value
                elif "secretKeyRef" in value_from:
                    secret_name = value_from["secretKeyRef"]["name"]
                    encoded = get_secret(namespace, secret_name)
                    key = value_from["secretKeyRef"]["key"]
                    if key not in encoded["data"]:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in encoded["data"]:
                        logger.warning(
                            f"{name} won't be set: key {key} not found in Secret {secret_name}"
                        )
                        value = ""
                    else:
                        value = decode(encoded["data"][key])
                    result[name] = value
                else:
                    logger.warning(
                        f"Unknown valueFrom format: {value_from} for {name} ({env})"
                    )
            else:
                logger.warning(f"Unknown env format: {env}")
    return result
