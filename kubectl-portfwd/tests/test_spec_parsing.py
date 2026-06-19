import pytest
from portfwd.domain.errors import InvalidTargetSpecError
from portfwd.domain.models import (
    PortForwardSpec,
    TargetKind,
    TargetRef,
)
from portfwd.presentation.spec_parser import parse_spec


def _spec(name, namespace=None, remote=None, local=None, kind=TargetKind.POD):
    return PortForwardSpec(
        target=TargetRef(kind=kind, name=name, namespace=namespace),
        remote_port=remote,
        local_port=local,
    )


@pytest.mark.parametrize(
    "tested, expected",
    [
        # The type segment is required; "type/name" is the trailing reference.
        ("pod/api", _spec(name="api", kind=TargetKind.POD)),
        ("svc/api", _spec(name="api", kind=TargetKind.SERVICE)),
        ("default/pod/api", _spec(name="api", namespace="default")),
        ("pod/api:80", _spec(name="api", remote=80)),
        (
            "default/svc/api:443",
            _spec(name="api", namespace="default", remote=443, kind=TargetKind.SERVICE),
        ),
        ("pod/api:80::8080", _spec(name="api", remote=80, local=8080)),
        (
            "default/pod/api:443::8443",
            _spec(name="api", namespace="default", remote=443, local=8443),
        ),
        ("pod/api:1", _spec(name="api", remote=1)),
        ("pod/api:65535", _spec(name="api", remote=65535)),
        ("pod/api:1::65535", _spec(name="api", remote=1, local=65535)),
        ("pod/api:8080::8080", _spec(name="api", remote=8080, local=8080)),
        (" pod/api ", _spec(name="api")),
        (
            "  default/svc/api:80  ",
            _spec(name="api", namespace="default", remote=80, kind=TargetKind.SERVICE),
        ),
        ("  pod/api:80::8080  ", _spec(name="api", remote=80, local=8080)),
        ("pod/api::8080  ", _spec(name="api", local=8080)),
        # Type aliases.
        ("po/api:80", _spec(name="api", remote=80, kind=TargetKind.POD)),
        ("pods/api", _spec(name="api", kind=TargetKind.POD)),
        ("service/api:80", _spec(name="api", remote=80, kind=TargetKind.SERVICE)),
        ("services/api", _spec(name="api", kind=TargetKind.SERVICE)),
        # Deployment aliases.
        ("deploy/api", _spec(name="api", kind=TargetKind.DEPLOYMENT)),
        ("deployment/api", _spec(name="api", kind=TargetKind.DEPLOYMENT)),
        ("deployments/api", _spec(name="api", kind=TargetKind.DEPLOYMENT)),
        (
            "default/deployment/api:8080",
            _spec(
                name="api", namespace="default", remote=8080, kind=TargetKind.DEPLOYMENT
            ),
        ),
        (
            "ns/deploy/api:80::9000",
            _spec(
                name="api",
                namespace="ns",
                remote=80,
                local=9000,
                kind=TargetKind.DEPLOYMENT,
            ),
        ),
    ],
)
def test_from_string_valid(tested, expected):
    assert parse_spec(tested) == expected


@pytest.mark.parametrize(
    "tested",
    [
        "",
        " ",
        # A missing type segment is rejected (no implicit default).
        "api",
        "default/api",
        "api:80",
        "/api",
        "pod/",
        "default/",
        "default/pod/api/extra",
        "pod/api:",
        "pod/api:abc",
        "pod/api:80::",
        "pod/api:80::abc",
    ],
)
def test_from_string_invalid_syntax(tested):
    """Rejects untyped or malformed values before Pydantic port validation."""
    with pytest.raises(
        InvalidTargetSpecError, match="expected \\[namespace/\\]\\[type/\\]name"
    ):
        parse_spec(tested)


def test_format_invalid_spec_includes_example():
    """format_invalid_spec produces a message listing pod, service, and deployment as valid types."""
    from portfwd.presentation.spec_parser import format_invalid_spec

    message = format_invalid_spec("ns/nginx:80:50001")
    assert message == (
        'invalid "ns/nginx:80:50001"; '
        "expected [namespace/][type/]name[:remote_port][::local_port] (type: pod | service | deployment); "
        "example ns-kubectl-portfwd/pod/nginx:80::50001"
    )


@pytest.mark.parametrize(
    "tested",
    [
        "pod/api:0",
        "pod/api:70000",
        "pod/api:80->0",
        "pod/api:80->70000",
    ],
)
def test_from_string_invalid_port_range(tested):
    from pydantic import ValidationError

    with pytest.raises((InvalidTargetSpecError, ValidationError)):
        parse_spec(tested)
