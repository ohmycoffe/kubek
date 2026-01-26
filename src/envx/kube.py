from __future__ import annotations

import json
import logging
import subprocess
from functools import lru_cache
from typing import Any

from envx.utils import decode

logger = logging.getLogger(__name__)


def call_subprocess(cmd: list[str]) -> str:
    logger.debug("Running command: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.exception("%s", e.stderr)
        raise
    return result.stdout


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


def extract_envs_from_container(
    namespace: str, container: dict[str, Any]
) -> dict[str, str]:
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
