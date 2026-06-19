from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.dto.container import Container
from kubek.kube.dto.kind import Kind


class PodMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class PodSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[Container] = Field(default_factory=list)


class Pod(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[Kind.POD] | None = Kind.POD
    metadata: PodMetadata
    spec: PodSpec


class PodList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Pod]
