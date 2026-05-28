import re

from portfwd.domain.errors import InvalidServiceSpecError
from portfwd.domain.models import NamespacedServiceNameSpec, ServicePortForwardSpec

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


def parse_spec(value: str) -> ServicePortForwardSpec:
    """Parse ``[namespace/]name[:remote_port][::local_port]`` into a spec."""

    argument = value.strip()
    match = REGEXP_PORT_FORWARD_SPEC.match(argument) if argument else None
    if not match:
        raise InvalidServiceSpecError(
            f'error: invalid value "{value}": expected format "[namespace/]name[:remote_port][::local_port]"'
        )

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
