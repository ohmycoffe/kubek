from pydantic import BaseModel, ConfigDict, Field


class NamespacedServiceNameSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    namespace: str | None = Field(default=None, min_length=1)

    def __str__(self) -> str:
        if self.namespace:
            return f"{self.namespace}/{self.name}"
        return self.name


class NamespacedServiceName(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)

    def __str__(self) -> str:
        return f"{self.namespace}/{self.name}"


class ServicePortForwardSpec(BaseModel):
    """Represents a port forward specification as provided by the user in their input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target: NamespacedServiceNameSpec
    remote_port: int | None = Field(default=None, ge=1, le=65535)
    local_port: int | None = Field(default=None, ge=1, le=65535)


class ServicePortForwardPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: NamespacedServiceName
    remote_port: int = Field(ge=1, le=65535)
    local_port: int = Field(ge=1, le=65535)
