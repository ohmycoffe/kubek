import asyncio
from types import SimpleNamespace

import pytest
from kubek.kube.dto.service import Service
from portfwd.application.ports import PortForwardEventStream
from portfwd.application.use_case import PortForwardUseCase
from portfwd.domain.config import GroupSpec, PortFwdConfig, ServicePortForwardDefaults
from portfwd.domain.errors import UnknownGroupError
from portfwd.domain.models import (
    NamespacedServiceNameSpec,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)


async def _empty_event_stream():
    return
    yield  # pragma: no cover


class SpyRunner(PortForwardEventStream):
    """Records every call to stream() without executing real kubectl."""

    def __init__(self) -> None:
        self.calls: list[list[ServicePortForwardPlan]] = []

    def stream(self, plans: list[ServicePortForwardPlan]):
        self.calls.append(plans)
        return _empty_event_stream()


def _make_api(namespace: str | None = "ns", services: dict | None = None) -> object:
    """Minimal fake KubeFacade covering only attributes used by PortForwardUseCase."""
    services_map = {(ns, name): svc for (ns, name), svc in (services or {}).items()}

    class FakeServiceRepo:
        def get(self, name: str, namespace: str | None = None) -> Service | None:
            return services_map.get((namespace, name))

    return SimpleNamespace(
        current_config=SimpleNamespace(namespace=namespace, context=None),
        service=FakeServiceRepo(),
    )


def _make_service(name: str, namespace: str, ports: list[int]) -> Service:
    return Service.model_validate(
        {
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
        }
    )


def test_stream_group_resolves_group_and_passes_converted_plans_to_runner():
    """stream_group fetches the named group and runs its services as plans."""
    defaults = ServicePortForwardDefaults(
        name="auth", namespace="ns", remote_port=80, local_port=9000
    )
    group = GroupSpec(name="backend", services=[defaults])
    config = PortFwdConfig(groups=[group])
    runner = SpyRunner()
    uc = PortForwardUseCase(config=config, streamer=runner, api=_make_api())

    async def consume() -> None:
        async for _ in uc.stream_group("backend"):
            pass

    asyncio.run(consume())

    assert len(runner.calls) == 1
    plans = runner.calls[0]
    assert len(plans) == 1
    assert plans[0].target.name == "auth"
    assert plans[0].target.namespace == "ns"
    assert plans[0].remote_port == 80
    assert plans[0].local_port == 9000


def test_stream_group_raises_unknown_group_when_group_is_missing():
    """stream_group propagates UnknownGroupError when the group name is not in config."""
    config = PortFwdConfig(groups=[GroupSpec(name="alpha", services=[])])
    runner = SpyRunner()
    uc = PortForwardUseCase(config=config, streamer=runner, api=_make_api())

    async def consume() -> None:
        async for _ in uc.stream_group("missing"):
            pass

    with pytest.raises(UnknownGroupError):
        asyncio.run(consume())


def test_stream_group_with_multiple_services_passes_all_plans():
    """All services in the group are converted to plans and passed to the runner."""
    services = [
        ServicePortForwardDefaults(
            name="svc-a", namespace="ns", remote_port=80, local_port=9001
        ),
        ServicePortForwardDefaults(
            name="svc-b", namespace="ns", remote_port=443, local_port=9002
        ),
    ]
    config = PortFwdConfig(groups=[GroupSpec(name="all", services=services)])
    runner = SpyRunner()
    uc = PortForwardUseCase(config=config, streamer=runner, api=_make_api())

    async def consume() -> None:
        async for _ in uc.stream_group("all"):
            pass

    asyncio.run(consume())

    plans = runner.calls[0]
    assert len(plans) == 2
    names = {p.target.name for p in plans}
    assert names == {"svc-a", "svc-b"}


def test_stream_specs_builds_plan_from_spec_and_passes_to_runner():
    """stream_specs resolves each spec to a plan and forwards them to the runner."""
    svc = _make_service("auth", "ns", [80])
    api = _make_api(namespace="ns", services={("ns", "auth"): svc})
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="auth", namespace="ns"),
        remote_port=80,
        local_port=9000,
    )
    runner = SpyRunner()
    uc = PortForwardUseCase(config=PortFwdConfig(), streamer=runner, api=api)

    async def consume() -> None:
        async for _ in uc.stream_specs([spec]):
            pass

    asyncio.run(consume())

    assert len(runner.calls) == 1
    plans = runner.calls[0]
    assert len(plans) == 1
    assert plans[0].target.name == "auth"
    assert plans[0].remote_port == 80
    assert plans[0].local_port == 9000


def test_stream_specs_passes_empty_list_to_runner_when_no_specs():
    """stream_specs passes an empty plan list to the runner when given no specs."""
    runner = SpyRunner()
    uc = PortForwardUseCase(config=PortFwdConfig(), streamer=runner, api=_make_api())

    async def consume() -> None:
        async for _ in uc.stream_specs([]):
            pass

    asyncio.run(consume())

    assert runner.calls == [[]]
