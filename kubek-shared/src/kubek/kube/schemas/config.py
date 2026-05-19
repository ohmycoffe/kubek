from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kubek.kube.schemas.base import Kind


class ContextData(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: str | None = None


class Context(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    context: ContextData


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[Kind.CONFIG] = Kind.CONFIG
    contexts: list[Context]
    current_context: str | None = Field(alias="current-context")

    @property
    def current_namespace(self) -> str | None:
        if not self.contexts:
            return None
        return next(
            (
                c.context.namespace
                for c in self.contexts
                if c.name == self.current_context
            ),
            None,
        )
