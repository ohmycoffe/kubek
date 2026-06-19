from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TargetKind(StrEnum):
    """A port-forward target type. Values are the prefixes kubectl expects."""

    POD = "pod"
    SERVICE = "svc"
    DEPLOYMENT = "deployment"


TARGET_KIND_LABELS: dict[TargetKind, str] = {
    TargetKind.SERVICE: "Services",
    TargetKind.POD: "Pods",
    TargetKind.DEPLOYMENT: "Deployments",
}


class TargetRef(BaseModel):
    """A user-provided reference to a port-forward target (namespace optional)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: TargetKind
    name: str = Field(min_length=1)
    namespace: str | None = Field(default=None, min_length=1)

    def __str__(self) -> str:
        if self.namespace:
            return f"{self.kind}/{self.namespace}/{self.name}"
        return f"{self.kind}/{self.name}"


class ResolvedTargetRef(BaseModel):
    """A fully-resolved port-forward target with a concrete namespace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: TargetKind
    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)

    def __str__(self) -> str:
        return f"{self.kind}/{self.namespace}/{self.name}"


class PortForwardSpec(BaseModel):
    """Represents a port forward specification as provided by the user in their input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target: TargetRef
    remote_port: int | None = Field(default=None, ge=1, le=65535)
    local_port: int | None = Field(default=None, ge=1, le=65535)


class PortForwardPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: ResolvedTargetRef
    remote_port: int = Field(ge=1, le=65535)
    local_port: int = Field(ge=1, le=65535)
