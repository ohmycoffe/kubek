from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServicePortForwardDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    remote_port: int = Field(ge=1, le=65535)
    local_port: int = Field(ge=1, le=65535)


class SpecialGroups(StrEnum):
    CUSTOM = "custom"


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
        self,
        name: str,
        namespace: str,
        remote_port: int,
    ) -> ServicePortForwardDefaults | None:
        candidates = [
            entry
            for entry in self.defaults
            if (
                entry.name == name
                and entry.namespace == namespace
                and entry.remote_port == remote_port
            )
        ]
        # if multiple defaults match, use the last one.
        return candidates[-1] if candidates else None
