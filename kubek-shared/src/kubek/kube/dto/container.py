from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ConfigMapKeyRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    key: str


class SecretKeyRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    key: str


class EnvValueFrom(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )

    config_map_key_ref: ConfigMapKeyRef | None = None
    secret_key_ref: SecretKeyRef | None = None


class EnvVar(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )

    name: str
    value: str | None = None
    value_from: EnvValueFrom | None = None


class ConfigMapRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class SecretRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class EnvFromSource(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )

    config_map_ref: ConfigMapRef | None = None
    secret_ref: SecretRef | None = None


class Container(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )

    env: list[EnvVar] | None = Field(default_factory=list)
    env_from: list[EnvFromSource] | None = Field(default_factory=list)
