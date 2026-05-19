from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.schemas import Container, Kind


class DeploymentMetadata(BaseModel):
    name: str
    namespace: str


class TemplateSpec(BaseModel):
    containers: list[Container] = Field(default_factory=list)


class Template(BaseModel):
    spec: TemplateSpec


class DeploymentSpec(BaseModel):
    template: Template


class Deployment(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: DeploymentMetadata
    spec: DeploymentSpec
    kind: Literal[Kind.DEPLOYMENT] = Kind.DEPLOYMENT


class DeploymentList(BaseModel):
    items: list[Deployment]
