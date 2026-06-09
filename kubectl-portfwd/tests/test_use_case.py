import asyncio
from types import SimpleNamespace

import pytest
from kubek.kube.dto.service import Service
from portfwd.application.ports import PortForwardRunner
from portfwd.application.use_case import PortForwardUseCase
from portfwd.domain.config import GroupSpec, PortFwdConfig, ServicePortForwardDefaults
from portfwd.domain.errors import UnknownGroupError
from portfwd.domain.models import (
    NamespacedServiceNameSpec,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)


class SpyRunner(PortForwardRunner):
    """Records every call to run() without executing real kubectl."""

    def __init__(self) -> None:
        self.calls: list[list[ServicePortForwardPlan]] = []

    async def run(self, plans: list[ServicePortForwardPlan]) -> None:
        self.calls.append(plans)


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


def test_run_group_resolves_group_and_passes_converted_plans_to_runner():
    """run_group fetches the named group and runs its services as plans."""
    defaults = ServicePortForwardDefaults(
        name="auth", namespace="ns", remote_port=80, local_port=9000
    )
    group = GroupSpec(name="backend", services=[defaults])
    config = PortFwdConfig(groups=[group])
    runner = SpyRunner()
    uc = PortForwardUseCase(config=config, runner=runner, api=_make_api())

    asyncio.run(uc.run_group("backend"))

    assert len(runner.calls) == 1
    plans = runner.calls[0]
    assert len(plans) == 1
    assert plans[0].target.name == "auth"
    assert plans[0].target.namespace == "ns"
    assert plans[0].remote_port == 80
    assert plans[0].local_port == 9000


def test_run_group_raises_unknown_group_when_group_is_missing():
    """run_group propagates UnknownGroupError when the group name is not in config."""
    config = PortFwdConfig(groups=[GroupSpec(name="alpha", services=[])])
    runner = SpyRunner()
    uc = PortForwardUseCase(config=config, runner=runner, api=_make_api())

    with pytest.raises(UnknownGroupError):
        asyncio.run(uc.run_group("missing"))


def test_run_group_with_multiple_services_passes_all_plans():
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
    uc = PortForwardUseCase(config=config, runner=runner, api=_make_api())

    asyncio.run(uc.run_group("all"))

    plans = runner.calls[0]
    assert len(plans) == 2
    names = {p.target.name for p in plans}
    assert names == {"svc-a", "svc-b"}


def test_run_specs_builds_plan_from_spec_and_passes_to_runner():
    """run_specs resolves each spec to a plan and forwards them to the runner."""
    svc = _make_service("auth", "ns", [80])
    api = _make_api(namespace="ns", services={("ns", "auth"): svc})
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="auth", namespace="ns"),
        remote_port=80,
        local_port=9000,
    )
    runner = SpyRunner()
    uc = PortForwardUseCase(config=PortFwdConfig(), runner=runner, api=api)

    asyncio.run(uc.run_specs([spec]))

    assert len(runner.calls) == 1
    plans = runner.calls[0]
    assert len(plans) == 1
    assert plans[0].target.name == "auth"
    assert plans[0].remote_port == 80
    assert plans[0].local_port == 9000


def test_run_specs_passes_empty_list_to_runner_when_no_specs():
    """run_specs passes an empty plan list to the runner when given no specs."""
    runner = SpyRunner()
    uc = PortForwardUseCase(config=PortFwdConfig(), runner=runner, api=_make_api())

    asyncio.run(uc.run_specs([]))

    assert runner.calls == [[]]
