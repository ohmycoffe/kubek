import base64

import pytest
from kubek.kube.dto.secret import Secret, SecretList
from kubek.kube.errors import KubeClientError


def _encoded(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def _make_secret(name: str, plain_data: dict[str, str]) -> Secret:
    return Secret.model_validate(
        {
            "metadata": {"name": name},
            "data": {k: _encoded(v) for k, v in plain_data.items()},
        }
    )


def test_decoded_returns_plain_text_value():
    secret = _make_secret("my-secret", {"password": "supersecret"})
    assert secret.decoded("password") == "supersecret"


def test_decoded_handles_empty_string_value():
    secret = _make_secret("my-secret", {"empty": ""})
    assert secret.decoded("empty") == ""


def test_decoded_raises_key_error_for_missing_key():
    secret = _make_secret("my-secret", {"password": "hunter2"})
    with pytest.raises(KeyError):
        secret.decoded("nonexistent")


def test_decoded_raises_kube_client_error_for_invalid_base64():
    # "abc" has 3 chars — binascii raises Incorrect padding
    secret = Secret.model_validate(
        {"metadata": {"name": "bad"}, "data": {"key": "abc"}}
    )
    with pytest.raises(KubeClientError):
        secret.decoded("key")


def test_decoded_raises_kube_client_error_for_non_utf8_bytes():
    non_utf8_b64 = base64.b64encode(b"\xff\xfe").decode()
    secret = Secret.model_validate(
        {"metadata": {"name": "bad"}, "data": {"key": non_utf8_b64}}
    )
    with pytest.raises(KubeClientError):
        secret.decoded("key")


def test_decoded_dict_returns_all_keys_decoded():
    secret = _make_secret("db-creds", {"user": "admin", "pass": "s3cr3t"})
    assert secret.decoded_dict() == {"user": "admin", "pass": "s3cr3t"}


def test_decoded_dict_returns_empty_dict_when_no_data():
    secret = Secret.model_validate({"metadata": {"name": "empty"}, "data": {}})
    assert secret.decoded_dict() == {}


def test_secret_list_parses_multiple_secrets():
    raw = {
        "items": [
            {"metadata": {"name": "a"}, "data": {"k": _encoded("v1")}},
            {"metadata": {"name": "b"}, "data": {"k": _encoded("v2")}},
        ]
    }
    result = SecretList.model_validate(raw)
    assert len(result.items) == 2
    assert result.items[0].metadata.name == "a"
    assert result.items[1].decoded("k") == "v2"
