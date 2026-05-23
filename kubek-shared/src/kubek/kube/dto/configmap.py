from pydantic import BaseModel, ConfigDict


class ConfigMapMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class ConfigMap(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: ConfigMapMetadata
    data: dict[str, str]


class ConfigMapList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ConfigMap]
