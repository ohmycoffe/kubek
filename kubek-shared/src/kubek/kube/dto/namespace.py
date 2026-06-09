from typing import Literal

from pydantic import BaseModel, ConfigDict

from kubek.kube.dto.kind import Kind


class NamespaceMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class Namespace(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[Kind.NAMESPACE] | None = Kind.NAMESPACE
    metadata: NamespaceMetadata


class NamespaceList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Namespace]
