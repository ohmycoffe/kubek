from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.dto.namespace import Namespace, NamespaceMetadata
from kubek.kube.dto.service import (
    Service,
    ServiceMetadata,
    ServicePortModel,
    ServiceSpec,
)
from kubek.term.output import create_output
from kubek.term.style import Color
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.application.port_forwarding.streamer import PortForwardEventStreamer
from portfwd.application.ports import (
    KubeGateway,
    PortForwardLauncher,
    PortForwardSession,
)
from portfwd.application.use_case import PortForwardUseCase
from portfwd.presentation.cli import run_port_forwards_from_cli
from portfwd.presentation.display import PortForwardLiveDisplay


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
            spec=ServiceSpec(ports=[ServicePortModel(port=30, protocol="TCP")]),
        ),
        Service(
            metadata=ServiceMetadata(name="svc-bar", namespace="ns-kubectl-portfwd"),
            spec=ServiceSpec(ports=[ServicePortModel(port=40, protocol="TCP")]),
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
    return cast(KubeGateway, res)


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
    def __init__(self, responses: list[dict]) -> None:
        self.responses = iter(responses)

    async def launch(self, plan) -> PortForwardSession:
        kwargs = next(self.responses)

        return FakePortForwardSession(
            snapshot=PortForwardProcessSnapshot(
                namespace=plan.target.namespace,
                service_name=plan.target.name,
                remote_port=plan.remote_port,
                local_port=plan.local_port,
                **kwargs,
            )
        )


def extract_cells(
    display: PortForwardLiveDisplay,
) -> list[list]:
    table = display._table.render()
    return [list(col.cells) for col in table.columns]


def test_run_from_spec():
    svc1, svc2 = build_services()
    expected_snapshot_1 = PortForwardProcessSnapshot(
        namespace=svc1.metadata.namespace,
        service_name=svc1.metadata.name,
        remote_port=svc1.spec.ports[0].port,
        local_port=3030,
        pid=123,
        returncode=1,
    )
    expected_snapshot_2 = PortForwardProcessSnapshot(
        namespace=svc2.metadata.namespace,
        service_name=svc2.metadata.name,
        remote_port=svc2.spec.ports[0].port,
        local_port=4040,
        pid=456,
        returncode=10,
    )

    api = create_fake_api()
    display = PortForwardLiveDisplay(
        context=api.current_config.context,
        console=create_output().console,
    )
    launcher = FakePortForwardLauncher(
        responses=[
            {
                "pid": expected_snapshot_1.pid,
                "returncode": expected_snapshot_1.returncode,
            },
            {
                "pid": expected_snapshot_2.pid,
                "returncode": expected_snapshot_2.returncode,
            },
        ]
    )
    use_case = PortForwardUseCase(
        streamer=PortForwardEventStreamer(launcher=launcher),
        api=api,
    )

    run_port_forwards_from_cli(
        file=None,
        service=[
            f"{expected_snapshot_1.namespace}/{expected_snapshot_1.service_name}:{expected_snapshot_1.remote_port}::{expected_snapshot_1.local_port}",
            f"{expected_snapshot_2.namespace}/{expected_snapshot_2.service_name}:{expected_snapshot_2.remote_port}::{expected_snapshot_2.local_port}",
        ],
        api=api,
        out=create_output(),
        use_case=use_case,
        display=display,
    )

    cells = extract_cells(display)
    assert cells == [
        [expected_snapshot_1.namespace, expected_snapshot_2.namespace],
        [expected_snapshot_1.service_name, expected_snapshot_2.service_name],
        [f":{expected_snapshot_1.remote_port}", f":{expected_snapshot_2.remote_port}"],
        [
            f"localhost:{expected_snapshot_1.local_port}",
            f"localhost:{expected_snapshot_2.local_port}",
        ],
        [str(expected_snapshot_1.pid), str(expected_snapshot_2.pid)],
        [
            f"[{Color.ERROR}]✗ died (exit {expected_snapshot_1.returncode})[/{Color.ERROR}]",
            f"[{Color.ERROR}]✗ died (exit {expected_snapshot_2.returncode})[/{Color.ERROR}]",
        ],
    ]


def test_run_from_spec_file(tmp_path: Path):
    svc1, _ = build_services()
    expected_snapshot_1 = PortForwardProcessSnapshot(
        namespace=svc1.metadata.namespace,
        service_name=svc1.metadata.name,
        remote_port=svc1.spec.ports[0].port,
        local_port=3030,
        pid=123,
        returncode=1,
    )

    spec_file = tmp_path / ".portfwd-plan"
    spec_file.write_text(
        f"{expected_snapshot_1.namespace}/{expected_snapshot_1.service_name}:"
        f"{expected_snapshot_1.remote_port}::{expected_snapshot_1.local_port}\n",
        encoding="utf-8",
    )

    api = create_fake_api()
    display = PortForwardLiveDisplay(
        context=api.current_config.context,
        console=create_output().console,
    )
    launcher = FakePortForwardLauncher(
        responses=[
            {
                "pid": expected_snapshot_1.pid,
                "returncode": expected_snapshot_1.returncode,
            },
        ]
    )
    use_case = PortForwardUseCase(
        streamer=PortForwardEventStreamer(launcher=launcher),
        api=api,
    )

    run_port_forwards_from_cli(
        file=spec_file,
        service=None,
        api=api,
        out=create_output(),
        use_case=use_case,
        display=display,
    )

    cells = extract_cells(display)
    assert cells == [
        [expected_snapshot_1.namespace],
        [expected_snapshot_1.service_name],
        [f":{expected_snapshot_1.remote_port}"],
        [f"localhost:{expected_snapshot_1.local_port}"],
        [str(expected_snapshot_1.pid)],
        [
            f"[{Color.ERROR}]✗ died (exit {expected_snapshot_1.returncode})[/{Color.ERROR}]"
        ],
    ]
