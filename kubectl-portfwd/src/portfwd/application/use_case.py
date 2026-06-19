from __future__ import annotations

from collections.abc import AsyncIterator

from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.application.port_forwarding.planner import build_port_forward_plan
from portfwd.application.ports import KubeGateway, PortForwardEventStream
from portfwd.domain.models import (
    PortForwardSpec,
)


class PortForwardUseCase:
    def __init__(
        self,
        api: KubeGateway,
        streamer: PortForwardEventStream,
    ) -> None:
        self._streamer = streamer
        self._api = api

    async def stream_specs(
        self, specs: list[PortForwardSpec]
    ) -> AsyncIterator[PortForwardEvent]:
        """Resolve specs to plans and yield port-forward lifecycle events."""
        plans = [build_port_forward_plan(spec=spec, api=self._api) for spec in specs]
        async for event in self._streamer.stream(plans):
            yield event
