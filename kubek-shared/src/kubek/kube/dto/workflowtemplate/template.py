from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from kubek.kube.dto.container import Container


class WorkflowTemplateType(StrEnum):
    DAG = "dag"
    STEPS = "steps"
    SCRIPT = "script"
    CONTAINER = "container"
    OTHER = "other"


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


class OtherTemplate(BaseModel):
    """Any Argo template type we don't use, e.g. suspend, resource or http."""

    model_config = ConfigDict(frozen=True)

    kind: Literal[WorkflowTemplateType.OTHER] = WorkflowTemplateType.OTHER
    name: str


class ArgoContainer(Container):
    """Unlike a Pod container, an Argo template container may omit the name."""

    name: str = "main"


class Parameters(BaseModel):
    name: str
    default: str | None = None


class Inputs(BaseModel):
    parameters: list[Parameters] | None = None


class ContainerTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[WorkflowTemplateType.CONTAINER] = WorkflowTemplateType.CONTAINER
    name: str
    container: ArgoContainer
    inputs: Inputs | None = None
