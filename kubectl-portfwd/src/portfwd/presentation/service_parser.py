import re

from portfwd.domain.errors import InvalidServiceSpecError
from portfwd.domain.models import NamespacedServiceNameSpec, ServicePortForwardSpec

SPEC_FORMAT = "[namespace/]name[:remote_port][::local_port]"
SPEC_EXAMPLE = "ns-kubectl-portfwd/nginx:80::50001"


REGEXP_PORT_FORWARD_SPEC = re.compile(
    r"""
    ^
    (?:(?P<namespace>[^/\s:]+)/)?
    (?P<name>[^/\s:]+)
    (?:
        :(?P<remote>\d+)
        (?:::(?P<local>\d+))?
        |
        ::(?P<local_only>\d+)
    )?
    $
    """,
    re.VERBOSE,
)


def format_invalid_spec(value: str) -> str:
    """Build a single-line message for a malformed ``--service`` value."""
    return f'invalid "{value}"; expected {SPEC_FORMAT}; example {SPEC_EXAMPLE}'


def format_spec_file_line_error(*, path: str, line: int, text: str) -> str:
    """Build a single-line message for a malformed spec file line."""
    return (
        f'invalid spec in {path} at line {line}: "{text}"; '
        f"expected {SPEC_FORMAT}; example {SPEC_EXAMPLE}"
    )


def parse_spec(value: str) -> ServicePortForwardSpec:
    """Parse ``[namespace/]name[:remote_port][::local_port]`` into a spec."""

    argument = value.strip()
    match = REGEXP_PORT_FORWARD_SPEC.match(argument) if argument else None
    if not match:
        raise InvalidServiceSpecError(format_invalid_spec(value))

    target = NamespacedServiceNameSpec(
        namespace=match.group("namespace"),
        name=match.group("name"),
    )
    local = match.group("local") or match.group("local_only")
    return ServicePortForwardSpec(
        target=target,
        remote_port=match.group("remote"),  # type: ignore[arg-type]
        local_port=local,  # type: ignore[arg-type]
    )
