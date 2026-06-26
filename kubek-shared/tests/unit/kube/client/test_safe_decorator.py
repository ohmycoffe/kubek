import ssl
from dataclasses import dataclass

import aiohttp
import pytest
from kubek.kube._infrastructure.client import safe
from kubek.kube.errors import (
    KubeAccessDeniedError,
    KubeApiNotFoundError,
    KubeAuthenticationError,
    KubeClientError,
)
from kubernetes.aio import client


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
async def test_handle_api_error(response: FakeHttpResponse, expected_exception):
    @safe
    async def fn():
        raise client.ApiException(http_resp=response)

    with pytest.raises(expected_exception) as exc_info:
        await fn()
    exc = exc_info.value
    assert exc.context() == {
        "status": response.status,
        "reason": response.reason,
        "body": response.data,
    }


async def test_passes_non_kube_exceptions_through():
    @safe
    async def fn():
        raise ValueError("not a kube error")

    with pytest.raises(ValueError):
        await fn()


async def test_passes_return_value_through():
    @safe
    async def fn():
        return {"ok": True}

    assert await fn() == {"ok": True}


async def test_authentication_error_includes_hint():
    @safe
    async def fn():
        raise client.ApiException(
            http_resp=FakeHttpResponse(
                status=401,
                reason="Unauthorized",
                data='{"message": "Unauthorized"}',
            )
        )

    with pytest.raises(KubeAuthenticationError) as exc_info:
        await fn()

    assert "re-authenticate" in str(exc_info.value)


async def test_passes_aiohttp_connection_errors_through():
    ssl_error = ssl.SSLCertVerificationError(
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
    )

    @safe
    async def fn():
        raise aiohttp.ClientConnectorCertificateError(
            connection_key=None,
            certificate_error=ssl_error,
        )

    with pytest.raises(aiohttp.ClientConnectorCertificateError):
        await fn()
