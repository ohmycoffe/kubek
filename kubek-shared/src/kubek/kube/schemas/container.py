from pydantic import BaseModel, Field


class ConfigMapKeyRef(BaseModel):
    name: str
    key: str


class SecretKeyRef(BaseModel):
    name: str
    key: str


class EnvValueFrom(BaseModel):
    configMapKeyRef: ConfigMapKeyRef | None = None
    secretKeyRef: SecretKeyRef | None = None


class EnvVar(BaseModel):
    name: str
    value: str | None = None
    valueFrom: EnvValueFrom | None = None


class ConfigMapRef(BaseModel):
    name: str


class SecretRef(BaseModel):
    name: str


class EnvFromSource(BaseModel):
    configMapRef: ConfigMapRef | None = None
    secretRef: SecretRef | None = None


class Container(BaseModel):
    env: list[EnvVar] = Field(default_factory=list)
    envFrom: list[EnvFromSource] = Field(default_factory=list)
