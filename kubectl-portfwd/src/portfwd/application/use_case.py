from __future__ import annotations

import itertools
from collections.abc import Iterable

from kubek.kube import KubeFacade, Service
from portfwd.application.plan import build_port_forward_plan
from portfwd.application.ports import PortForwardRunner
from portfwd.domain.config import GroupSpec, PortFwdConfig
from portfwd.domain.errors import (
    NoGroupsDefinedError,
    UnknownGroupError,
)
from portfwd.domain.models import (
    NamespacedServiceNamePlan,
    NamespacedServiceNameSpec,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)


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


class PortForwardUseCase:
    def __init__(
        self,
        config: PortFwdConfig,
        runner: PortForwardRunner,
        api: KubeFacade,
    ) -> None:
        self._config = config
        self._runner = runner
        self._api = api

    @property
    def groups(self) -> list[GroupSpec]:
        return self._config.groups

    async def run_specs(self, specs: list[ServicePortForwardSpec]) -> None:
        plans = [
            build_port_forward_plan(spec=spec, config=self._config, api=self._api)
            for spec in specs
        ]

        await self._runner.run(plans)

    async def run_group(self, group_name: str) -> None:
        group = self._resolve_group(group_name)
        plans = [
            ServicePortForwardPlan(
                target=NamespacedServiceNamePlan(
                    name=svc.name, namespace=svc.namespace
                ),
                remote_port=svc.remote_port,
                local_port=svc.local_port,
            )
            for svc in group.services
        ]
        await self._runner.run(plans)

    def _resolve_group(self, name: str) -> GroupSpec:
        groups = self._config.groups

        if not groups:
            raise NoGroupsDefinedError("no groups defined in config file")

        for group in groups:
            if group.name == name:
                return group

        names = ", ".join(sorted(group.name for group in groups))
        raise UnknownGroupError(f'unknown group "{name}" (available: {names})')
