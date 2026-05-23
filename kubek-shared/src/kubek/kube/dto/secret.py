import base64
from binascii import Error

from pydantic import BaseModel, ConfigDict

from kubek.kube.errors import ClientException


class SecretMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class Secret(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: SecretMetadata
    data: dict[str, str]

    def decoded(self, key: str) -> str:
        if key not in self.data:
            raise KeyError(key)
        try:
            return base64.b64decode(self.data[key]).decode("utf-8")
        except (Error, UnicodeDecodeError) as e:
            raise ClientException(
                f"secret {self.metadata.name!r} key {key!r} is not valid base64/utf-8",
            ) from e

    def decoded_dict(self) -> dict[str, str]:
        return {k: self.decoded(k) for k in self.data}


class SecretList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Secret]
