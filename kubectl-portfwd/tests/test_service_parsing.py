import pytest
from portfwd.domain.errors import InvalidServiceSpecError
from portfwd.domain.models import NamespacedServiceNameSpec, ServicePortForwardSpec
from portfwd.presentation.service_parser import parse_spec


def _spec(name, namespace=None, remote=None, local=None):
    return ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name=name, namespace=namespace),
        remote_port=remote,
        local_port=local,
    )


@pytest.mark.parametrize(
    "tested, expected",
    [
        ("api", _spec(name="api")),
        ("default/api", _spec(name="api", namespace="default")),
        ("api:80", _spec(name="api", remote=80)),
        ("default/api:443", _spec(name="api", namespace="default", remote=443)),
        ("api:80::8080", _spec(name="api", remote=80, local=8080)),
        (
            "default/api:443::8443",
            _spec(name="api", namespace="default", remote=443, local=8443),
        ),
        ("api:1", _spec(name="api", remote=1)),
        ("api:65535", _spec(name="api", remote=65535)),
        ("api:1::65535", _spec(name="api", remote=1, local=65535)),
        ("api:8080::8080", _spec(name="api", remote=8080, local=8080)),
        (" api ", _spec(name="api")),
        ("  default/api:80  ", _spec(name="api", namespace="default", remote=80)),
        ("  api:80::8080  ", _spec(name="api", remote=80, local=8080)),
        ("api::8080  ", _spec(name="api", local=8080)),
    ],
)
def test_from_string_valid(tested, expected):
    assert parse_spec(tested) == expected


@pytest.mark.parametrize(
    "tested",
    [
        "",
        " ",
        "/api",
        "default/",
        "a/b/c",
        "api:",
        "api:abc",
        "api:80::",
        "api:80::abc",
    ],
)
def test_from_string_invalid_syntax(tested):
    """Rejects malformed --service values before Pydantic port validation."""
    with pytest.raises(InvalidServiceSpecError, match="expected \\[namespace/\\]name"):
        parse_spec(tested)


def test_format_invalid_spec_includes_example():
    from portfwd.presentation.service_parser import format_invalid_spec

    message = format_invalid_spec("ns/nginx:80:50001")
    assert message == (
        'invalid "ns/nginx:80:50001"; '
        "expected [namespace/]name[:remote_port][::local_port]; "
        "example ns-kubectl-portfwd/nginx:80::50001"
    )


@pytest.mark.parametrize(
    "tested",
    [
        "api:0",
        "api:70000",
        "api:80->0",
        "api:80->70000",
    ],
)
def test_from_string_invalid_port_range(tested):
    from pydantic import ValidationError

    with pytest.raises((InvalidServiceSpecError, ValidationError)):
        parse_spec(tested)
