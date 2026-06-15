from __future__ import annotations

from collections.abc import AsyncIterator

from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.application.port_forwarding.planner import build_port_forward_plan
from portfwd.application.ports import KubeGateway, PortForwardEventStream
from portfwd.domain.config import GroupSpec, PortFwdConfig
from portfwd.domain.models import (
    ServicePortForwardSpec,
)


class PortForwardUseCase:
    def __init__(
        self,
        api: KubeGateway,
        config: PortFwdConfig,
        streamer: PortForwardEventStream,
    ) -> None:
        self._config = config
        self._streamer = streamer
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
        async for event in self._streamer.stream(plans):
            yield event

    async def stream_group(self, group_name: str) -> AsyncIterator[PortForwardEvent]:
        """Run a configured service group and yield port-forward lifecycle events."""
        group = self._config.get_group(group_name)
        plans = [s.to_plan() for s in group.services]
        async for event in self._streamer.stream(plans):
            yield event
