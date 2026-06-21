import re

from portfwd.domain.errors import InvalidTargetSpecError
from portfwd.domain.models import (
    PortForwardSpec,
    TargetKind,
    TargetRef,
)

SPEC_FORMAT = "[namespace/][type/]name[:remote_port][::local_port] (type: pod | service | deployment | statefulset | daemonset | replicaset | job | cronjob)"
SPEC_EXAMPLE = "ns-kubectl-portfwd/pod/nginx:80::50001"

# kubectl-style resource type aliases for the required ``type/`` segment.
_KIND_ALIASES: dict[str, TargetKind] = {
    "pod": TargetKind.POD,
    "po": TargetKind.POD,
    "pods": TargetKind.POD,
    "svc": TargetKind.SERVICE,
    "service": TargetKind.SERVICE,
    "services": TargetKind.SERVICE,
    "deployment": TargetKind.DEPLOYMENT,
    "deploy": TargetKind.DEPLOYMENT,
    "deployments": TargetKind.DEPLOYMENT,
    "statefulset": TargetKind.STATEFULSET,
    "sts": TargetKind.STATEFULSET,
    "statefulsets": TargetKind.STATEFULSET,
    "daemonset": TargetKind.DAEMONSET,
    "ds": TargetKind.DAEMONSET,
    "daemonsets": TargetKind.DAEMONSET,
    "replicaset": TargetKind.REPLICASET,
    "rs": TargetKind.REPLICASET,
    "replicasets": TargetKind.REPLICASET,
    "job": TargetKind.JOB,
    "jobs": TargetKind.JOB,
    "cronjob": TargetKind.CRONJOB,
    "cronjobs": TargetKind.CRONJOB,
    "cj": TargetKind.CRONJOB,
}


def _kind_pattern() -> str:
    return "|".join(sorted(_KIND_ALIASES, key=len, reverse=True))


# The type segment is required (no implicit default), so every spec names its
# kind explicitly. The kubectl-style "type/name" reference (e.g. "pod/api") is
# the trailing part, optionally scoped by a leading "namespace/" ("ns/pod/api").
REGEXP_PORT_FORWARD_SPEC = re.compile(
    rf"""
    ^
    (?:(?P<namespace>[^/\s:]+)/)?
    (?P<kind>{_kind_pattern()})/
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
    """Build a single-line message for a malformed ``--target`` value."""
    return f'invalid "{value}"; expected {SPEC_FORMAT}; example {SPEC_EXAMPLE}'


def format_spec_file_line_error(*, path: str, line: int, text: str) -> str:
    """Build a single-line message for a malformed spec file line."""
    return (
        f'invalid spec in {path} at line {line}: "{text}"; '
        f"expected {SPEC_FORMAT}; example {SPEC_EXAMPLE}"
    )


def parse_spec(value: str) -> PortForwardSpec:
    """Parse ``[namespace/]type/name[:remote_port][::local_port]`` into a spec.

    The ``type/`` segment (e.g. ``svc/``, ``pod/``) is required; a spec without
    one is rejected so the target kind is never guessed.
    """

    argument = value.strip()
    match = REGEXP_PORT_FORWARD_SPEC.match(argument) if argument else None
    if not match:
        raise InvalidTargetSpecError(format_invalid_spec(value))

    kind = _KIND_ALIASES[match.group("kind")]
    target = TargetRef(
        kind=kind,
        namespace=match.group("namespace"),
        name=match.group("name"),
    )
    local = match.group("local") or match.group("local_only")
    return PortForwardSpec(
        target=target,
        remote_port=match.group("remote"),  # type: ignore[arg-type]
        local_port=local,  # type: ignore[arg-type]
    )
