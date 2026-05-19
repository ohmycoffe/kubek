import re

from portfwd.models import NamespacedServiceNameSpec, ServicePortForwardSpec

REGEXP_PORT_FORWARD_SPEC = re.compile(
    r"""
    ^
    (?:(?P<namespace>[^/\s:]+)/)?     # optional namespace
    (?P<name>[^/\s:]+)               # service name
    (?:
        :
        (?P<remote>\d+)              # remote port
        (?:
            ::
            (?P<local>\d+)           # optional local port
        )?
    )?
    $
    """,
    re.VERBOSE,
)


def parse_spec(value: str) -> ServicePortForwardSpec:
    """Parse ``[namespace/]name[:remote_port][::local_port]`` into a spec."""

    argument = value.strip()
    match = REGEXP_PORT_FORWARD_SPEC.match(argument) if argument else None
    if not match:
        raise ValueError(
            f'error: invalid value "{value}": expected format "[namespace/]name[:remote_port][::local_port]"'
        )

    target = NamespacedServiceNameSpec(
        namespace=match.group("namespace"),
        name=match.group("name"),
    )

    return ServicePortForwardSpec(
        target=target,
        remote_port=match.group("remote"),  # type: ignore[arg-type]
        local_port=match.group("local"),  # type: ignore[arg-type]
    )
