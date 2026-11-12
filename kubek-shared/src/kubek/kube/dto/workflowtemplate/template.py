from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

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

    @field_validator("container", mode="before")
    @classmethod
    def default_container_name(cls, value: Any) -> Any:
        # Unlike a Pod container, an Argo container may omit the name.
        if isinstance(value, dict) and "name" not in value:
            return {"name": "main", **value}
        return value
