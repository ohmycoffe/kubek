from pydantic import BaseModel, Field


class Metadata(BaseModel):
    name: str
    namespace: str


class ServicePortModel(BaseModel):
    port: int
    protocol: str


class Spec(BaseModel):
    ports: list[ServicePortModel] = Field(default_factory=list)


class Service(BaseModel):
    metadata: Metadata
    spec: Spec


class ServiceList(BaseModel):
    items: list[Service]
