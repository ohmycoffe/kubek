from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.dto.container import Container
from kubek.kube.dto.kind import Kind


class JobMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class TemplateSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[Container] = Field(default_factory=list)


class Template(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: TemplateSpec


class JobSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    template: Template


class Job(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: JobMetadata
    spec: JobSpec
    kind: Literal[Kind.JOB] | None = Kind.JOB


class JobList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Job]
