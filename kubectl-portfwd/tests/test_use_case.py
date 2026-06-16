from types import SimpleNamespace
from typing import cast

import pytest
from kubek.kube.dto.service import Service
from portfwd.application.ports import KubeGateway, PortForwardEventStream
from portfwd.application.use_case import PortForwardUseCase
from portfwd.domain.models import (
    NamespacedServiceNameSpec,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)


class SpyRunner(PortForwardEventStream):
    """Records every call to stream() without executing real kubectl."""

    def __init__(self) -> None:
        self.calls: list[list[ServicePortForwardPlan]] = []

    def stream(self, plans: list[ServicePortForwardPlan]):
        self.calls.append(plans)
        return self._empty_event_stream()

    @staticmethod
    async def _empty_event_stream():
        # yield makes this an async generator (an async iterator). The unreachable
        # yield lets stream() return something `async for` can consume with zero events.
        return
        yield  # pragma: no cover


def _make_api(
    namespace: str | None = "ns", services: dict | None = None
) -> KubeGateway:
    """Minimal fake KubeFacade covering only attributes used by PortForwardUseCase."""
    services_map = {(ns, name): svc for (ns, name), svc in (services or {}).items()}

    class FakeServiceRepo:
        def get(self, name: str, namespace: str | None = None) -> Service | None:
            return services_map.get((namespace, name))

    return cast(
        KubeGateway,
        SimpleNamespace(
            current_config=SimpleNamespace(namespace=namespace, context=None),
            service=FakeServiceRepo(),
        ),
    )


def _make_service(name: str, namespace: str, ports: list[int]) -> Service:
    return Service.model_validate(
        {
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
        }
    )


@pytest.mark.asyncio
async def test_stream_specs_builds_plan_from_spec_and_passes_to_runner():
    """stream_specs resolves each spec to a plan and forwards them to the runner."""
    svc = _make_service("auth", "ns", [80])
    api = _make_api(namespace="ns", services={("ns", "auth"): svc})
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="auth", namespace="ns"),
        remote_port=80,
        local_port=9000,
    )
    runner = SpyRunner()
    uc = PortForwardUseCase(streamer=runner, api=api)

    async for _ in uc.stream_specs([spec]):
        pass

    assert len(runner.calls) == 1
    plans = runner.calls[0]
    assert len(plans) == 1
    assert plans[0].target.name == "auth"
    assert plans[0].remote_port == 80
    assert plans[0].local_port == 9000


@pytest.mark.asyncio
async def test_stream_specs_passes_empty_list_to_runner_when_no_specs():
    """stream_specs passes an empty plan list to the runner when given no specs."""
    runner = SpyRunner()
    uc = PortForwardUseCase(streamer=runner, api=_make_api())

    async for _ in uc.stream_specs([]):
        pass

    assert runner.calls == [[]]
