from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".kube" / "portfwd"


class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    remote_port: int = Field(ge=1, le=65535)
    local_port: int = Field(ge=1, le=65535)


class QualifiedName(BaseModel):
    model_config = ConfigDict(extra="forbid")
    namespace: str = Field(min_length=1)
    name: str = Field(min_length=1)

    def __str__(self) -> str:
        return f"{self.namespace}/{self.name}"

    def __hash__(self) -> int:
        return hash((self.namespace, self.name))

    @classmethod
    def from_string(cls, value: str) -> QualifiedName:
        parts = value.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid reference '{value}', expected 'namespace/name'")
        return cls(namespace=parts[0], name=parts[1])


class GroupRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    services: list[QualifiedName] = Field(default_factory=list)

    @field_validator("services", mode="before")
    @classmethod
    def validate_qualnames(cls, v):
        errors = []
        parsed = []

        for idx, item in enumerate(v):
            if isinstance(item, QualifiedName):
                parsed.append(item)
                continue
            try:
                parsed.append(QualifiedName.from_string(item))
            except ValueError as e:
                errors.append(
                    {
                        "type": "value_error",
                        "loc": ("services", idx),
                        "msg": e,
                        "input": str(item),
                    }
                )

        if errors:
            raise ValidationError.from_exception_data(cls.__name__, errors)

        return parsed


class PortFwdConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ports: list[ServiceConfig] = Field(
        default_factory=list,
        validation_alias="port_forwards",
    )
    groups: list[GroupRef] = Field(default_factory=list)

    @field_validator("groups", mode="before")
    @classmethod
    def convert_groups_dict(cls, v):
        if isinstance(v, dict):
            return [
                {"name": name, "services": services} for name, services in v.items()
            ]
        return v


def load_config(path: Path | None) -> PortFwdConfig:
    if path is None:
        path = DEFAULT_CONFIG_PATH

    if not path.exists():
        logger.debug("No config file found at %s, using empty config", path)
        return PortFwdConfig()

    yaml = YAML(typ="safe")
    try:
        with path.open(encoding="utf-8") as f:
            root = yaml.load(f)
        if not isinstance(root, dict):
            logger.warning(
                "Config at %s has unexpected structure, using empty config", path
            )
            return PortFwdConfig()
        logger.info("Loaded config from %s", path)
        return PortFwdConfig.model_validate(root)
    except Exception as e:
        logger.warning("Failed to load config from %s: %s, using empty config", path, e)
        return PortFwdConfig()
