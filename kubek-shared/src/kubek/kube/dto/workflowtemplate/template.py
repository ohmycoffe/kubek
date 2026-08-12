from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from kubek.kube.dto.container import Container

DEFAULT_CONTAINER_NAME = "main"


class WorkflowContainer(Container):
    """A container inside an Argo workflow template, where ``name`` is optional.

    Kubernetes requires a name on every pod container, so ``Container`` makes it
    mandatory. Argo does not: when it turns a template into a pod it renames the
    container to ``main`` anyway, so writing a name has no effect and most
    manifests leave it out. Argo allows that by removing ``name`` from the
    required fields of its CRD, and the API happily returns containers without
    one -- which used to fail validation here.

    Hence this separate class. ``Container`` stays strict for Deployments, Jobs
    and Pods, where a name really is guaranteed. Here a missing name becomes
    ``main``, the name Argo would give it; a name the API did return is kept
    as-is, even though Argo will override it.
    """

    name: str = DEFAULT_CONTAINER_NAME


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
    container: WorkflowContainer
    inputs: Inputs | None = None
