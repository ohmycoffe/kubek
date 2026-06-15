from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.dto.namespace import Namespace, NamespaceMetadata
from kubek.kube.dto.service import (
    Service,
    ServiceMetadata,
    ServicePortModel,
    ServiceSpec,
)
from kubek.term.output import create_output
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.application.port_forwarding.streamer import PortForwardEventStreamer
from portfwd.application.ports import (
    KubeGateway,
    PortForwardLauncher,
    PortForwardSession,
)
from portfwd.application.use_case import PortForwardUseCase
from portfwd.domain.config import PortFwdConfig, SpecialGroups
from portfwd.domain.models import (
    NamespacedServiceNameSpec,
    ServicePortForwardSpec,
)
from portfwd.presentation.cli import run_port_forwards_from_cli
from portfwd.presentation.display import PortForwardLiveDisplay


class _InMemoryRepository:
    def __init__(self, items):
        self.items = items

    def list(self, namespace: str | None = None):
        if namespace is None:
            return self.items
        return [x for x in self.items if x.metadata.namespace == namespace]

    def get(self, name: str, namespace: str | None = None):
        assert namespace is not None
        return next(
            (
                x
                for x in self.items
                if x.metadata.name == name and x.metadata.namespace == namespace
            ),
            None,
        )


def _build_services() -> list[Service]:
    return [
        Service(
            metadata=ServiceMetadata(name="svc-foo", namespace="ns-kubectl-portfwd"),
            spec=ServiceSpec(ports=[ServicePortModel(port=30, protocol="TCP")]),
        ),
        Service(
            metadata=ServiceMetadata(name="svc-bar", namespace="ns-kubectl-portfwd"),
            spec=ServiceSpec(ports=[ServicePortModel(port=40, protocol="TCP")]),
        ),
    ]


def _create_fake_api() -> KubeGateway:
    namespace = Namespace(metadata=NamespaceMetadata(name="ns-kubectl-portfwd"))
    return cast(
        KubeGateway,
        SimpleNamespace(
            namespace=_InMemoryRepository([namespace]),
            service=_InMemoryRepository(_build_services()),
            current_config=ResolvedKubeConfig(
                context="test", namespace="ns-kubectl-portfwd"
            ),
        ),
    )


class _FakePortForwardSession(PortForwardSession):
    def __init__(self, snapshot: PortForwardProcessSnapshot) -> None:
        self._snapshot = snapshot
        self.wait_mock = AsyncMock(return_value=None)
        self.terminate_mock = Mock(return_value=None)

    def snapshot(self) -> PortForwardProcessSnapshot:
        return self._snapshot

    def terminate(self) -> None:
        self.terminate_mock()

    async def wait(self) -> None:
        await self.wait_mock()


class _FakePortForwardLauncher(PortForwardLauncher):
    def __init__(self, responses: list[dict]) -> None:
        self.responses = iter(responses)

    async def launch(self, plan) -> PortForwardSession:
        kwargs = next(self.responses)
        return _FakePortForwardSession(
            snapshot=PortForwardProcessSnapshot(
                namespace=plan.target.namespace,
                service_name=plan.target.name,
                remote_port=plan.remote_port,
                local_port=plan.local_port,
                **kwargs,
            )
        )


def test_run_port_forwards_raises_when_group_and_service_both_provided():
    """group and service flags are mutually exclusive at the dispatch layer."""
    api = _create_fake_api()
    use_case = PortForwardUseCase(
        config=PortFwdConfig(),
        streamer=PortForwardEventStreamer(launcher=_FakePortForwardLauncher([])),
        api=api,
    )

    with pytest.raises(ValueError, match="cannot both be provided"):
        run_port_forwards_from_cli(
            cfg=PortFwdConfig(),
            group="backend",
            service=["ns/svc:80::8080"],
            api=api,
            out=create_output(),
            use_case=use_case,
            display=PortForwardLiveDisplay(context=None),
        )


def test_run_port_forwards_custom_flow_uses_selected_services():
    """Interactive custom flow fetches services and forwards the user's selection."""
    api = _create_fake_api()
    svc1, _ = _build_services()
    selected = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(
            name=svc1.metadata.name,
            namespace=svc1.metadata.namespace,
        ),
        remote_port=svc1.spec.ports[0].port,
        local_port=3030,
    )
    use_case = PortForwardUseCase(
        config=PortFwdConfig(),
        streamer=PortForwardEventStreamer(
            launcher=_FakePortForwardLauncher([{"pid": 123, "returncode": 0}])
        ),
        api=api,
    )
    display = PortForwardLiveDisplay(context=api.current_config.context)

    with (
        patch(
            "portfwd.presentation.cli.ask_for_group",
            return_value=SpecialGroups.CUSTOM,
        ),
        patch(
            "portfwd.presentation.cli.ask_for_namespace",
            return_value=["ns-kubectl-portfwd"],
        ),
        patch(
            "portfwd.presentation.cli.ask_for_service",
            return_value=[selected],
        ),
    ):
        run_port_forwards_from_cli(
            cfg=PortFwdConfig(),
            group=None,
            service=None,
            api=api,
            out=create_output(),
            use_case=use_case,
            display=display,
        )

    cells = [list(col.cells) for col in display._table.render().columns]
    assert cells[1] == [svc1.metadata.name]
