from __future__ import annotations

from kubek.kube import KubeFacade
from portfwd.application.port_forward_planner import build_port_forward_plan
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

    async def run_specs(self, specs: list[ServicePortForwardSpec]) -> None:
        plans = [
            build_port_forward_plan(spec=spec, config=self._config, api=self._api)
            for spec in specs
        ]

        await self._runner.run(plans)

    async def run_group(self, group_name: str) -> None:
        group = self._config.get_group(group_name)
        plans = [s.to_plan() for s in group.services]
        await self._runner.run(plans)
