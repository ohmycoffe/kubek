from typing import Literal

from pydantic import BaseModel, ConfigDict

from kubek.kube.schemas.base import Kind


class Metadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class Namespace(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[Kind.NAMESPACE] = Kind.NAMESPACE
    metadata: Metadata


class NamespaceList(BaseModel):
    items: list[Namespace]
