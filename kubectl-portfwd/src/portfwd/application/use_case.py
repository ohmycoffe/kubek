from __future__ import annotations

from collections.abc import AsyncIterator

from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.application.port_forwarding.planner import build_port_forward_plan
from portfwd.application.ports import KubeGateway, PortForwardEventStream
from portfwd.domain.errors import DuplicateLocalPortError
from portfwd.domain.models import (
    PortForwardPlan,
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
        plans = [
            await build_port_forward_plan(spec=spec, api=self._api) for spec in specs
        ]
        self._check_no_duplicate_local_ports(plans)
        async for event in self._streamer.stream(plans):
            yield event

    @staticmethod
    def _check_no_duplicate_local_ports(plans: list[PortForwardPlan]) -> None:
        seen: dict[int, PortForwardPlan] = {}

        for plan in plans:
            if plan.local_port in seen:
                first = seen[plan.local_port]
                raise DuplicateLocalPortError(
                    f"Duplicate local port {plan.local_port}: "
                    f'"{first.target}" and "{plan.target}" cannot be forwarded at the same time.'
                )
            seen[plan.local_port] = plan
