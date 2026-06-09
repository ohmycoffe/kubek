import base64

import pytest
from kubek.kube.dto.secret import Secret, SecretList
from kubek.kube.errors import KubeClientError


def _encoded(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def _make_secret(name: str, plain_data: dict[str, str]) -> Secret:
    return Secret.model_validate(
        {
            "metadata": {"name": name, "namespace": "default"},
            "data": {key: _encoded(value) for key, value in plain_data.items()},
        }
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("password", "supersecret"),
        ("empty", ""),
    ],
)
def test_decoded_returns_plain_text_value(key: str, value: str) -> None:
    secret = _make_secret("my-secret", {key: value})

    assert secret.decoded(key) == value


def test_decoded_raises_key_error_for_missing_key() -> None:
    secret = _make_secret("my-secret", {"password": "hunter2"})

    with pytest.raises(KeyError):
        secret.decoded("nonexistent")


@pytest.mark.parametrize(
    "encoded_value",
    [
        "abc",  # invalid base64 padding
        base64.b64encode(b"\xff\xfe").decode(),  # valid base64, invalid UTF-8
    ],
)
def test_decoded_raises_kube_client_error_for_invalid_encoded_value(
    encoded_value: str,
) -> None:
    secret = Secret.model_validate(
        {
            "metadata": {"name": "bad", "namespace": "default"},
            "data": {"key": encoded_value},
        }
    )

    with pytest.raises(KubeClientError):
        secret.decoded("key")


def test_decoded_dict_returns_all_keys_decoded() -> None:
    secret = _make_secret("db-creds", {"user": "admin", "pass": "s3cr3t"})

    assert secret.decoded_dict() == {"user": "admin", "pass": "s3cr3t"}


def test_decoded_dict_returns_empty_dict_when_no_data() -> None:
    secret = Secret.model_validate(
        {
            "metadata": {"name": "empty", "namespace": "default"},
            "data": {},
        }
    )

    assert secret.decoded_dict() == {}


def test_secret_list_parses_multiple_secrets() -> None:
    raw = {
        "items": [
            {
                "metadata": {"name": "a", "namespace": "default"},
                "data": {"k": _encoded("v1")},
            },
            {
                "metadata": {"name": "b", "namespace": "default"},
                "data": {"k": _encoded("v2")},
            },
        ]
    }

    result = SecretList.model_validate(raw)

    assert len(result.items) == 2
    assert result.items[0].metadata.name == "a"
    assert result.items[1].metadata.name == "b"
    assert result.items[1].decoded("k") == "v2"
