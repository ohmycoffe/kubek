from pydantic import BaseModel


class ConfigMapMetadata(BaseModel):
    name: str


class ConfigMap(BaseModel):
    metadata: ConfigMapMetadata
    data: dict[str, str]
