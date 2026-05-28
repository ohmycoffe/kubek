from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from portfwd.domain.errors import NoGroupsDefinedError, UnknownGroupError
from portfwd.domain.models import NamespacedServiceNamePlan, ServicePortForwardPlan


class ServicePortForwardDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    remote_port: int = Field(ge=1, le=65535)
    local_port: int = Field(ge=1, le=65535)

    def to_plan(self) -> ServicePortForwardPlan:
        return ServicePortForwardPlan(
            target=NamespacedServiceNamePlan(
                name=self.name,
                namespace=self.namespace,
            ),
            remote_port=self.remote_port,
            local_port=self.local_port,
        )


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

    def get_group(self, name: str) -> GroupSpec:
        if not self.groups:
            raise NoGroupsDefinedError("no groups defined in config file")

        for group in self.groups:
            if group.name == name:
                return group

        names = ", ".join(sorted(group.name for group in self.groups))
        raise UnknownGroupError(f'unknown group "{name}" (available: {names})')
