from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from kubek.kube.dto.container import Container
from kubek.kube.dto.kind import Kind


class CronJobMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class TemplateSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    containers: list[Container] = Field(default_factory=list)


class Template(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: TemplateSpec


class CronJobJobSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    template: Template


class JobTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: CronJobJobSpec


class CronJobSpec(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )

    job_template: JobTemplate


class CronJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: CronJobMetadata
    spec: CronJobSpec
    kind: Literal[Kind.CRONJOB] | None = Kind.CRONJOB


class CronJobList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CronJob]
