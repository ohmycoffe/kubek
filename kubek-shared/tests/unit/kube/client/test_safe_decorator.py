from dataclasses import dataclass

import pytest
import urllib3.exceptions
from kubek.kube._infrastructure.client import safe
from kubek.kube.errors import (
    KubeAccessDeniedError,
    KubeApiNotFoundError,
    KubeAuthenticationError,
    KubeClientError,
)
from kubernetes.client import ApiException


@dataclass
class FakeHttpResponse:
    status: int
    reason: str
    data: str | None

    def getheaders(self):
        return None


@pytest.mark.parametrize(
    "response,expected_exception",
    [
        (
            FakeHttpResponse(
                status=404, reason="Not Found", data='{"message": "Not Found"}'
            ),
            KubeApiNotFoundError,
        ),
        (
            FakeHttpResponse(
                status=403, reason="Forbidden", data='{"message": "Forbidden"}'
            ),
            KubeAccessDeniedError,
        ),
        (
            FakeHttpResponse(
                status=401, reason="Unauthorized", data='{"message": "Unauthorized"}'
            ),
            KubeAuthenticationError,
        ),
        (
            FakeHttpResponse(
                status=500,
                reason="Internal Server Error",
                data='{"message": "Internal Server Error"}',
            ),
            KubeClientError,
        ),
    ],
)
def test_handle_api_error(response: FakeHttpResponse, expected_exception):
    @safe
    def fn():
        raise ApiException(http_resp=response)

    with pytest.raises(expected_exception) as exc_info:
        fn()
    exc = exc_info.value
    assert exc.context() == {
        "status": response.status,
        "reason": response.reason,
        "body": response.data,
    }


def test_passes_non_kube_exceptions_through():
    @safe
    def fn():
        raise ValueError("not a kube error")

    with pytest.raises(ValueError):
        fn()


def test_passes_return_value_through():
    @safe
    def fn():
        return {"ok": True}

    assert fn() == {"ok": True}


def test_authentication_error_includes_hint():
    @safe
    def fn():
        raise ApiException(
            http_resp=FakeHttpResponse(
                status=401,
                reason="Unauthorized",
                data='{"message": "Unauthorized"}',
            )
        )

    with pytest.raises(KubeAuthenticationError) as exc_info:
        fn()

    assert "re-authenticate" in str(exc_info.value)


def test_connection_error_includes_tls_hint_for_ssl_failure():
    ssl_error = urllib3.exceptions.SSLError(
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
    )
    retry_error = urllib3.exceptions.MaxRetryError(
        urllib3.connectionpool.HTTPSConnectionPool(
            host="cluster.example.com",
            port=443,
        ),
        "/apis/apps/v1/namespaces/default/deployments/foo",
        reason=ssl_error,
    )

    @safe
    def fn():
        raise retry_error

    with pytest.raises(KubeClientError) as exc_info:
        fn()

    assert "--insecure-skip-tls-verify" in str(exc_info.value)
