from types import SimpleNamespace
from typing import cast

import pytest
from kubek.kube.dto.service import Service
from portfwd.application.ports import KubeGateway, PortForwardEventStream
from portfwd.application.use_case import PortForwardUseCase
from portfwd.domain.errors import DuplicateLocalPortError
from portfwd.domain.models import (
    PortForwardPlan,
    PortForwardSpec,
    TargetKind,
    TargetRef,
)


class SpyRunner(PortForwardEventStream):
    """Records every call to stream() without executing real kubectl."""

    def __init__(self) -> None:
        self.calls: list[list[PortForwardPlan]] = []

    def stream(self, plans: list[PortForwardPlan]):
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
    spec = PortForwardSpec(
        target=TargetRef(kind=TargetKind.SERVICE, name="auth", namespace="ns"),
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


@pytest.mark.asyncio
async def test_stream_specs_raises_on_duplicate_local_port():
    """stream_specs raises DuplicateLocalPortError when two plans share a local port."""
    svc_a = _make_service("alpha", "ns", [80])
    svc_b = _make_service("beta", "ns", [80])
    api = _make_api(
        namespace="ns",
        services={("ns", "alpha"): svc_a, ("ns", "beta"): svc_b},
    )
    spec_a = PortForwardSpec(
        target=TargetRef(kind=TargetKind.SERVICE, name="alpha", namespace="ns"),
        remote_port=80,
        local_port=9000,
    )
    spec_b = PortForwardSpec(
        target=TargetRef(kind=TargetKind.SERVICE, name="beta", namespace="ns"),
        remote_port=80,
        local_port=9000,
    )
    runner = SpyRunner()
    uc = PortForwardUseCase(streamer=runner, api=api)

    with pytest.raises(
        DuplicateLocalPortError,
        match="svc/ns/alpha.*svc/ns/beta|svc/ns/beta.*svc/ns/alpha",
    ):
        async for _ in uc.stream_specs([spec_a, spec_b]):
            pass
