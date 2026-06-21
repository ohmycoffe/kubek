from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.dto.container import Container
from kubek.kube.dto.kind import Kind


class ReplicaSetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class TemplateSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[Container] = Field(default_factory=list)


class Template(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: TemplateSpec


class ReplicaSetSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    template: Template


class ReplicaSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: ReplicaSetMetadata
    spec: ReplicaSetSpec
    kind: Literal[Kind.REPLICASET] | None = Kind.REPLICASET


class ReplicaSetList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ReplicaSet]
