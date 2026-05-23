from pydantic import BaseModel, ConfigDict, Field


class ServiceMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str


class ServicePortModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    port: int
    protocol: str


class Spec(BaseModel):
    model_config = ConfigDict(frozen=True)

    ports: list[ServicePortModel] = Field(default_factory=list)


class Service(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: ServiceMetadata
    spec: Spec


class ServiceList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Service]
