from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML, YAMLError

from portfwd.domain.config import PortFwdConfig, ServicePortForwardDefaults

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".kube" / "portfwd"


def get_default_service(
    config: PortFwdConfig,
    name: str,
    namespace: str,
    remote_port: int,
) -> ServicePortForwardDefaults | None:
    candidates = [
        entry
        for entry in config.defaults
        if (
            entry.name == name
            and entry.namespace == namespace
            and entry.remote_port == remote_port
        )
    ]
    # if multiple defaults match, use the last one.
    return candidates[-1] if candidates else None


def load_config(path: Path | None) -> PortFwdConfig:
    """Load port-forward config from YAML.

    When ``path`` is omitted, uses ``DEFAULT_CONFIG_PATH`` and returns an empty
    config if that file does not exist. When ``path`` is given explicitly,
    missing or invalid files raise instead of falling back silently.
    """
    explicit = path is not None
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        if explicit:
            raise FileNotFoundError(config_path)
        logger.debug("No config file found at %s, using empty config", config_path)
        return PortFwdConfig()

    yaml = YAML(typ="safe")
    try:
        with config_path.open(encoding="utf-8") as f:
            root = yaml.load(f)
    except YAMLError as e:
        if explicit:
            raise ValueError(f"Invalid YAML in config {config_path}: {e}") from e
        logger.warning(
            "Failed to parse config from %s: %s, using empty config", config_path, e
        )
        return PortFwdConfig()

    if not isinstance(root, dict):
        msg = (
            f"Config at {config_path} must be a YAML mapping, got {type(root).__name__}"
        )
        if explicit:
            raise ValueError(msg)
        logger.warning("%s, using empty config", msg)
        return PortFwdConfig()

    try:
        logger.info("Loaded config from %s", config_path)
        return PortFwdConfig.model_validate(root)
    except ValidationError:
        if explicit:
            raise
        logger.warning("Invalid config at %s, using empty config", config_path)
        return PortFwdConfig()
