from __future__ import annotations

from collections.abc import AsyncIterator

from kubek.kube import KubeFacade
from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.application.port_forwarding.planner import build_port_forward_plan
from portfwd.application.ports import PortForwardRunner
from portfwd.domain.config import GroupSpec, PortFwdConfig
from portfwd.domain.models import (
    ServicePortForwardSpec,
)


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

    async def stream_specs(
        self, specs: list[ServicePortForwardSpec]
    ) -> AsyncIterator[PortForwardEvent]:
        """Resolve specs to plans and yield port-forward lifecycle events."""
        plans = [
            build_port_forward_plan(spec=spec, config=self._config, api=self._api)
            for spec in specs
        ]
        async for event in self._runner.stream(plans):
            yield event

    async def stream_group(self, group_name: str) -> AsyncIterator[PortForwardEvent]:
        """Run a configured service group and yield port-forward lifecycle events."""
        group = self._config.get_group(group_name)
        plans = [s.to_plan() for s in group.services]
        async for event in self._runner.stream(plans):
            yield event
