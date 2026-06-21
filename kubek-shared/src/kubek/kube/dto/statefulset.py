from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.dto.container import Container
from kubek.kube.dto.kind import Kind


class StatefulSetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class TemplateSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[Container] = Field(default_factory=list)


class Template(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: TemplateSpec


class StatefulSetSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    template: Template


class StatefulSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: StatefulSetMetadata
    spec: StatefulSetSpec
    kind: Literal[Kind.STATEFULSET] | None = Kind.STATEFULSET


class StatefulSetList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[StatefulSet]
