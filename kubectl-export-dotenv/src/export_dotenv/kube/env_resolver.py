import logging
import re
from collections.abc import Callable
from functools import lru_cache

from kubek.kube import ConfigMap, Container, Secret

from export_dotenv.errors import UnsupportedFormatError
from export_dotenv.kube.gateway import KubeGateway

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


def extract_envs_from_container(
    api: KubeGateway,
    container: Container,
    fallback_keys: dict[str, str] | None = None,
) -> dict[str, str]:
    namespace = api.current_config.namespace

    @lru_cache
    def get_secret(name: str) -> Secret | None:
        return api.secret.get(name=name, namespace=namespace)

    @lru_cache
    def get_configmap(name: str) -> ConfigMap | None:
        return api.configmap.get(name=name, namespace=namespace)

    if fallback_keys is None:
        fallback_keys = {}

    result: dict[str, str] = {}

    if container.env_from:
        for env_from in container.env_from:
            if env_from.config_map_ref:
                configmap = get_configmap(env_from.config_map_ref.name)
                if not configmap:
                    cfg_map_name = env_from.config_map_ref.name
                    logger.warning("ConfigMap %s not found, skipping.", cfg_map_name)
                    continue
                result.update(configmap.data)
            elif env_from.secret_ref:
                secret_name = env_from.secret_ref.name
                secret = get_secret(secret_name)
                if not secret:
                    logger.warning("Secret %s not found, skipping.", secret_name)
                    continue
                result.update(secret.decoded_dict())
            else:
                raise UnsupportedFormatError(f"Unknown envFrom format: {env_from}")

    if container.env:
        for env in container.env:
            name = env.name
            if env.value is not None:
                value = env.value
                result[name] = value
            elif env.value_from:
                value_from = env.value_from
                if value_from.config_map_key_ref:
                    configmap = get_configmap(value_from.config_map_key_ref.name)
                    if configmap is None:
                        cfg_map_name = value_from.config_map_key_ref.name
                        logger.warning(
                            "ConfigMap %s not found, skipping.", cfg_map_name
                        )
                        continue
                    key = value_from.config_map_key_ref.key
                    if key not in configmap.data:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in configmap.data:
                        logger.warning(
                            "%s won't be set: key %s not found in ConfigMap %s",
                            name,
                            key,
                            value_from.config_map_key_ref.name,
                        )
                        value = ""
                    else:
                        value = configmap.data[key]
                    result[name] = value
                elif value_from.secret_key_ref:
                    secret_name = value_from.secret_key_ref.name
                    secret = get_secret(secret_name)
                    if secret is None:
                        logger.warning("Secret %s not found, skipping.", secret_name)
                        continue
                    key = value_from.secret_key_ref.key
                    if key not in secret.data:
                        key = fallback_keys.get(_clean_key(key), key)
                    if key not in secret.data:
                        logger.warning(
                            "%s won't be set: key %s not found in Secret %s",
                            name,
                            key,
                            secret_name,
                        )
                        value = ""
                    else:
                        value = secret.decoded(key)
                    result[name] = value
                elif value_from.field_ref or value_from.resource_field_ref:
                    # Downward API (fieldRef / resourceFieldRef) resolves at pod
                    # runtime and cannot be known from a static spec, so skip it.
                    continue
                else:
                    logger.warning(
                        "Unknown valueFrom format: %s for %s (%s)",
                        value_from,
                        name,
                        env,
                    )
            elif env.name:
                # If the env var has a name but no value or valueFrom, it is considered to have an empty value.
                result[name] = ""
            else:
                logger.warning("Unknown env format: %s", env)
    return result
