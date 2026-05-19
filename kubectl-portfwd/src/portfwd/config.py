from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from ruamel.yaml import YAML, YAMLError

from portfwd.constants import SpecialGroups

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".kube" / "portfwd"


class ServicePortForwardDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    remote_port: int = Field(ge=1, le=65535)
    local_port: int = Field(ge=1, le=65535)


class GroupSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    services: list[ServicePortForwardDefaults] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_not_reserved(cls, value: str) -> str:
        if value.lower() == SpecialGroups.CUSTOM:
            raise ValueError(
                f'error: invalid group name "{value}": name is reserved for interactive mode'
            )
        return value


class PortFwdConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    defaults: list[ServicePortForwardDefaults] = Field(default_factory=list)
    groups: list[GroupSpec] = Field(default_factory=list)


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


def get_group(cfg: PortFwdConfig, name: str) -> GroupSpec | None:
    for group in cfg.groups:
        if group.name == name:
            return group
    return None


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
