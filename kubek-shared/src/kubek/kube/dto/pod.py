from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from kubek.kube.dto.kind import Kind


class PodMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class PodContainerPort(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )

    container_port: int
    protocol: str | None = None


class PodContainer(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )

    ports: list[PodContainerPort] = Field(default_factory=list)


class PodSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[PodContainer] = Field(default_factory=list)


class Pod(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[Kind.POD] | None = Kind.POD
    metadata: PodMetadata
    spec: PodSpec


class PodList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Pod]
