from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.dto.container import Container
from kubek.kube.dto.kind import Kind


class DeploymentMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class TemplateSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[Container] = Field(default_factory=list)


class Template(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: TemplateSpec


class DeploymentSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    template: Template


class Deployment(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: DeploymentMetadata
    spec: DeploymentSpec
    kind: Literal[Kind.DEPLOYMENT] | None = Kind.DEPLOYMENT


class DeploymentList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Deployment]
