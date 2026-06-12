from contextlib import nullcontext
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock, call

from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.dto.namespace import Namespace, NamespaceMetadata
from kubek.kube.dto.service import (
    Service,
    ServiceMetadata,
    ServicePortModel,
    ServiceSpec,
)
from kubek.term.output import create_output
from portfwd.application.port_forwarding.events import (
    PortForwardEvent,
    PortForwardEventType,
)
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.application.port_forwarding.streamer import PortForwardEventStreamer
from portfwd.application.ports import (
    KubeGateway,
    PortForwardLauncher,
    PortForwardSession,
)
from portfwd.application.use_case import PortForwardUseCase
from portfwd.domain.config import PortFwdConfig
from portfwd.presentation.cli import run_port_forwards_from_cli


class InMemoryRepository:
    def __init__(self, items):
        self.items = items

    def list(self, namespace: str | None = None):
        assert namespace is not None, "namespace must be provided"
        return [x for x in self.items if x.metadata.namespace == namespace]

    def get(self, name: str, namespace: str | None = None):
        assert namespace is not None, "namespace must be provided"
        return next(
            (
                x
                for x in self.items
                if x.metadata.name == name and x.metadata.namespace == namespace
            ),
            None,
        )


def build_namespace():
    return Namespace(
        metadata=NamespaceMetadata(name="ns-kubectl-portfwd"),
    )


def build_services():
    return [
        Service(
            metadata=ServiceMetadata(name="svc-foo", namespace="ns-kubectl-portfwd"),
            spec=ServiceSpec(ports=[ServicePortModel(port=80, protocol="TCP")]),
        ),
        Service(
            metadata=ServiceMetadata(name="svc-bar", namespace="ns-kubectl-portfwd"),
            spec=ServiceSpec(ports=[ServicePortModel(port=80, protocol="TCP")]),
        ),
    ]


def create_fake_api() -> KubeGateway:
    res = SimpleNamespace(
        namespace=InMemoryRepository([build_namespace()]),
        service=InMemoryRepository(build_services()),
        current_config=ResolvedKubeConfig(
            context="test", namespace="ns-kubectl-portfwd"
        ),
    )
    return res  # type: ignore


class FakePortForwardSession(PortForwardSession):
    def __init__(self, snapshot: PortForwardProcessSnapshot) -> None:
        self.snapshot_mock = Mock(return_value=snapshot)
        self.wait_mock = AsyncMock(return_value=None)
        self.terminate_mock = Mock(return_value=None)

    def snapshot(self) -> PortForwardProcessSnapshot:
        return cast(PortForwardProcessSnapshot, self.snapshot_mock())

    def terminate(self) -> None:
        self.terminate_mock()

    async def wait(self) -> None:
        await self.wait_mock()


class FakePortForwardLauncher(PortForwardLauncher):
    async def launch(self, plan) -> PortForwardSession:
        return FakePortForwardSession(
            snapshot=PortForwardProcessSnapshot(
                namespace=plan.target.namespace,
                service_name=plan.target.name,
                remote_port=plan.remote_port,
                local_port=plan.local_port,
                pid=12345,
                returncode=1,
            )
        )


def test_run_from_spec():
    api = create_fake_api()
    display_mock = Mock()
    display_mock.live.return_value = nullcontext()
    cfg = PortFwdConfig(
        groups=[],
        defaults=[],
    )
    launcher = FakePortForwardLauncher()
    use_case = PortForwardUseCase(
        config=cfg,
        streamer=PortForwardEventStreamer(launcher=launcher),
        api=api,
    )

    run_port_forwards_from_cli(
        cfg=cfg,
        group=None,
        service=[
            "ns-kubectl-portfwd/svc-foo:80::3030",
            "ns-kubectl-portfwd/svc-bar:80::4040",
        ],
        api=api,
        out=create_output(),
        use_case=use_case,
        display=display_mock,
    )

    expected_snapshot_1 = PortForwardProcessSnapshot(
        namespace="ns-kubectl-portfwd",
        service_name="svc-foo",
        remote_port=80,
        local_port=3030,
        pid=12345,
        returncode=1,
    )
    expected_snapshot_2 = PortForwardProcessSnapshot(
        namespace="ns-kubectl-portfwd",
        service_name="svc-bar",
        remote_port=80,
        local_port=4040,
        pid=12345,
        returncode=1,
    )

    expected_events = [
        PortForwardEvent(
            type=PortForwardEventType.STARTED,
            snapshot=expected_snapshot_1,
        ),
        PortForwardEvent(
            type=PortForwardEventType.DIED,
            snapshot=expected_snapshot_1,
        ),
        PortForwardEvent(
            type=PortForwardEventType.STARTED,
            snapshot=expected_snapshot_2,
        ),
        PortForwardEvent(
            type=PortForwardEventType.DIED,
            snapshot=expected_snapshot_2,
        ),
    ]
    assert display_mock.apply.call_count == len(expected_events)
    display_mock.apply.assert_has_calls(
        [call(event) for event in expected_events],
        any_order=True,
    )
