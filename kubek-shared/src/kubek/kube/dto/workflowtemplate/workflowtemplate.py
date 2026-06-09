from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from kubek.kube.dto.kind import Kind

from .template import (
    ContainerTemplate,
    DagTemplate,
    ScriptTemplate,
    StepsTemplate,
)

Template = DagTemplate | StepsTemplate | ScriptTemplate | ContainerTemplate


def parse_template(data: dict | Template) -> Template:
    if isinstance(
        data, DagTemplate | StepsTemplate | ScriptTemplate | ContainerTemplate
    ):
        return data

    keys = ["dag", "steps", "script", "container"]
    found = [k for k in keys if k in data]

    if len(found) != 1:
        raise ValueError(f"Expected exactly one template type, got {found}: {data}")

    if "dag" in data:
        return DagTemplate(**data)

    if "steps" in data:
        return StepsTemplate(**data)

    if "script" in data:
        return ScriptTemplate(**data)

    if "container" in data:
        return ContainerTemplate(**data)

    raise ValueError(f"Unexpected template type: {data}")


class Metadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class WorkflowSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    templates: list[Template]

    @model_validator(mode="before")
    @classmethod
    def parse_templates(cls, data):
        raw_templates = data.get("templates", [])
        data["templates"] = [parse_template(t) for t in raw_templates]
        return data


class WorkflowTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: Metadata
    spec: WorkflowSpec
    kind: Literal[Kind.WORKFLOWTEMPLATE] = Kind.WORKFLOWTEMPLATE


class WorkflowTemplateList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WorkflowTemplate]
