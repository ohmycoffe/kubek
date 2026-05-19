import base64

from pydantic import BaseModel


class SecretMetadata(BaseModel):
    name: str


class Secret(BaseModel):
    metadata: SecretMetadata
    data: dict[str, str]

    @property
    def decoded_data(self) -> dict[str, str]:
        return {k: base64.b64decode(v).decode("utf-8") for k, v in self.data.items()}
