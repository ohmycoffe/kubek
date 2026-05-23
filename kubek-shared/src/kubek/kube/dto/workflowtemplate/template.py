from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from kubek.kube.dto.container import Container


class WorkflowTemplateType(StrEnum):
    DAG = "dag"
    STEPS = "steps"
    SCRIPT = "script"
    CONTAINER = "container"


class DagTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[WorkflowTemplateType.DAG] = WorkflowTemplateType.DAG
    name: str


class StepsTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[WorkflowTemplateType.STEPS] = WorkflowTemplateType.STEPS
    name: str


class ScriptTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[WorkflowTemplateType.SCRIPT] = WorkflowTemplateType.SCRIPT
    name: str


class Parameters(BaseModel):
    name: str
    default: str | None = None


class Inputs(BaseModel):
    parameters: list[Parameters] | None = None


class ContainerTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[WorkflowTemplateType.CONTAINER] = WorkflowTemplateType.CONTAINER
    name: str
    container: Container
    inputs: Inputs | None = None
