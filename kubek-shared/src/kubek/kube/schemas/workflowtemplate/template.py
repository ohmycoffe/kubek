from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from kubek.kube.schemas.container import Container


class TemplateType(StrEnum):
    DAG = "dag"
    STEPS = "steps"
    SCRIPT = "script"
    CONTAINER = "container"


class DagTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[TemplateType.DAG] = TemplateType.DAG
    name: str


class StepsTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[TemplateType.STEPS] = TemplateType.STEPS
    name: str


class ScriptTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[TemplateType.SCRIPT] = TemplateType.SCRIPT
    name: str


class Parameters(BaseModel):
    name: str
    default: str | None = None


class Inputs(BaseModel):
    parameters: list[Parameters] | None = None


class ContainerTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[TemplateType.CONTAINER] = TemplateType.CONTAINER
    name: str
    container: Container
    inputs: Inputs | None = None
