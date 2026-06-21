from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.dto.container import Container
from kubek.kube.dto.kind import Kind


class DaemonSetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class TemplateSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[Container] = Field(default_factory=list)


class Template(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: TemplateSpec


class DaemonSetSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    template: Template


class DaemonSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: DaemonSetMetadata
    spec: DaemonSetSpec
    kind: Literal[Kind.DAEMONSET] | None = Kind.DAEMONSET


class DaemonSetList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[DaemonSet]
