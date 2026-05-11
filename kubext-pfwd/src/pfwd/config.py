from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = (
    Path(
        os.environ.get(
            "XDG_CONFIG_HOME",
            Path.home() / ".config",
        )
    )
    / "kpf"
    / "config.toml"
)


class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    remote_port: int = Field(ge=1, le=65535)
    local_port: int = Field(ge=1, le=65535)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_namespace: str | None = None
    ports: list[ServiceConfig] = []


def load_config(path: Path | None) -> Config:
    if path is None:
        path = DEFAULT_CONFIG_PATH

    default_config = Config()

    if not path.exists():
        logger.debug("No config file found at %s, using defaults", path)
        return default_config

    with path.open("rb") as f:
        data = tomllib.load(f)
    try:
        config = Config.model_validate(data)
        logger.info("Loaded config from %s", path)
        return config
    except ValidationError as e:
        logger.warning(
            "Failed to parse config file at %s. Using defaults instead. "
            "To fix this, ensure your config file is valid TOML "
            "and matches the expected schema.",
            path,
        )
        logger.warning("%s", e)

        return default_config
