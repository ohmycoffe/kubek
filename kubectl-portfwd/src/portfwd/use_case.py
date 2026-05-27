from __future__ import annotations

import asyncio
import itertools
from collections.abc import Iterable

from kubek.kube import KubeFacade, Service
from kubek.term.output import CLIOutput

from portfwd.domain.config import GroupSpec, PortFwdConfig, SpecialGroups
from portfwd.domain.errors import (
    NoGroupsDefinedError,
    NoSelectionError,
    NoServicesFoundError,
    UnknownGroupError,
)
from portfwd.domain.models import (
    NamespacedServiceNamePlan,
    NamespacedServiceNameSpec,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)
from portfwd.parser import parse_spec
from portfwd.plan import build_port_forward_plan
from portfwd.prompts import ask_for_group, ask_for_namespace, ask_for_service
from portfwd.runner import manage_port_forwards


def run_port_forwards(
    *,
    cfg: PortFwdConfig,
    group: str | None,
    service: list[str] | None,
    api: KubeFacade,
    out: CLIOutput,
) -> None:
    """Dispatch to the correct port-forward flow based on CLI flags.

    - `--service` wins outright.
    - `--group` runs that group.
    - Otherwise prompt the user to pick a group (or 'custom' interactive flow).
    """
    if service is not None:
        run_services(service=service, cfg=cfg, api=api)
        return
    if group is not None:
        run_group(group_name=group, cfg=cfg, api=api)
        return

    selection = ask_for_group(cfg.groups)
    if selection is SpecialGroups.CUSTOM:
        run_interactive(cfg=cfg, api=api, out=out)
    else:
        run_group(group_name=selection.name, cfg=cfg, api=api)


def run_group(*, group_name: str, cfg: PortFwdConfig, api: KubeFacade) -> None:
    group = _resolve_group(group_name, cfg.groups)
    plans = [
        ServicePortForwardPlan(
            target=NamespacedServiceNamePlan(name=svc.name, namespace=svc.namespace),
            remote_port=svc.remote_port,
            local_port=svc.local_port,
        )
        for svc in group.services
    ]
    asyncio.run(manage_port_forwards(plans=plans, api=api))


def run_services(*, service: list[str], cfg: PortFwdConfig, api: KubeFacade) -> None:
    plans = [
        build_port_forward_plan(spec=parse_spec(s), config=cfg, api=api)
        for s in service
    ]
    asyncio.run(manage_port_forwards(plans=plans, api=api))


def run_interactive(*, cfg: PortFwdConfig, api: KubeFacade, out: CLIOutput) -> None:
    with out.progress("Fetching namespaces…"):
        namespaces = [ns.metadata.name for ns in api.namespace.list()]
    selected_namespaces = ask_for_namespace(namespaces, api.current_config.namespace)
    if not selected_namespaces:
        raise NoSelectionError("no namespaces selected")

    with out.progress("Fetching services…"):
        specs = _fetch_services_for_namespaces(selected_namespaces, api)
    if not specs:
        raise NoServicesFoundError("no services found in the selected namespaces")

    selected = ask_for_service(specs)
    if not selected:
        raise NoSelectionError("no services selected")

    plans = [build_port_forward_plan(spec=s, config=cfg, api=api) for s in selected]
    asyncio.run(manage_port_forwards(plans=plans, api=api))


def _resolve_group(name: str, available: list[GroupSpec]) -> GroupSpec:
    if not available:
        raise NoGroupsDefinedError("no groups defined in config file")
    for g in available:
        if g.name == name:
            return g
    names = ", ".join(sorted(g.name for g in available))
    raise UnknownGroupError(f'unknown group "{name}" (available: {names})')


def convert_services_to_specs(
    services: Iterable[Service],
) -> list[ServicePortForwardSpec]:
    """Flatten Service list to (target, remote_port) specs, sorted for the picker."""
    return [
        ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(
                namespace=svc.metadata.namespace,
                name=svc.metadata.name,
            ),
            remote_port=port.port,
        )
        for svc in sorted(
            services, key=lambda s: (s.metadata.namespace, s.metadata.name)
        )
        for port in sorted(svc.spec.ports, key=lambda x: x.port)
    ]


def _fetch_services_for_namespaces(
    namespaces: list[str], api: KubeFacade
) -> list[ServicePortForwardSpec]:
    raw = itertools.chain.from_iterable(
        api.service.list(namespace=ns) for ns in namespaces
    )
    return convert_services_to_specs(raw)
