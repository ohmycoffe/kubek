"""Reusable test doubles and helpers shared across the portfwd test-suite.

Importable as a package (the tests directory is on `sys.path`):

    from portfwd_test_utils.fakes import FakeSession, PlannedLauncher, make_fake_api
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast

from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.dto.container import Container, ContainerPort
from kubek.kube.dto.deployment import (
    Deployment,
    DeploymentMetadata,
    DeploymentSpec,
    Template,
    TemplateSpec,
)
from kubek.kube.dto.namespace import Namespace, NamespaceMetadata
from kubek.kube.dto.pod import (
    Pod,
    PodContainer,
    PodContainerPort,
    PodMetadata,
    PodSpec,
)
from kubek.kube.dto.service import (
    Service,
    ServiceMetadata,
    ServicePortModel,
    ServiceSpec,
)
from portfwd.application.port_forwarding.events import OutputLine
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.application.ports import (
    KubeGateway,
    PortForwardLauncher,
    PortForwardSession,
)
from portfwd.domain.models import TargetKind
from portfwd.presentation.display import PortForwardLiveDisplay

NAMESPACE = "ns-kubectl-portfwd"

# Status-table column positions, by header order.
COL_NAMESPACE = 0
COL_REMOTE = 1
COL_LOCAL = 2
COL_PID = 3
COL_STATUS = 4


def make_snapshot(
    *,
    kind: TargetKind = TargetKind.SERVICE,
    name: str = "svc",
    namespace: str = "ns",
    remote_port: int = 80,
    local_port: int = 9000,
    pid: int = 1234,
    returncode: int | None = None,
) -> PortForwardProcessSnapshot:
    """Build a process snapshot with sensible defaults for tests."""
    return PortForwardProcessSnapshot(
        kind=kind,
        namespace=namespace,
        name=name,
        remote_port=remote_port,
        local_port=local_port,
        pid=pid,
        returncode=returncode,
    )


class FakeSession(PortForwardSession):
    """A port-forward session that exits immediately, or blocks until terminated.

    `block_exit=True` keeps the session alive until `terminate()` is called,
    simulating a long-running port-forward.
    """

    def __init__(
        self,
        snapshot: PortForwardProcessSnapshot,
        *,
        block_exit: bool = False,
        output: list[OutputLine] | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._output = output or []
        self._exit = asyncio.Event()
        if not block_exit:
            self._exit.set()

    def snapshot(self) -> PortForwardProcessSnapshot:
        return self._snapshot

    async def wait(self) -> None:
        await self._exit.wait()

    def terminate(self) -> None:
        self._exit.set()

    async def stream_output(self) -> AsyncIterator[OutputLine]:
        for line in self._output:
            yield line


class StaticLauncher(PortForwardLauncher):
    """Always returns the same pre-built session."""

    def __init__(self, session: PortForwardSession) -> None:
        self._session = session

    async def launch(self, plan) -> PortForwardSession:
        return self._session


class SequentialLauncher(PortForwardLauncher):
    """Returns sessions in order, then repeats the last one."""

    def __init__(self, sessions: list[PortForwardSession]) -> None:
        self._sessions = sessions
        self._index = 0

    async def launch(self, plan) -> PortForwardSession:
        if self._index < len(self._sessions):
            session = self._sessions[self._index]
            self._index += 1
            return session
        return self._sessions[-1]


class FailingLauncher(PortForwardLauncher):
    """Fails `fail_count` times, then returns a long-running session."""

    def __init__(
        self,
        *,
        fail_count: int = 1,
        then_session: PortForwardSession | None = None,
    ) -> None:
        self._fail_count = fail_count
        self._then_session = then_session
        self._attempts = 0

    @property
    def attempts(self) -> int:
        return self._attempts

    async def launch(self, plan) -> PortForwardSession:
        self._attempts += 1
        if self._attempts <= self._fail_count:
            raise RuntimeError("launch failed")
        return self._then_session or FakeSession(
            make_snapshot(returncode=0), block_exit=True
        )


@dataclass(frozen=True)
class FakeLaunch:
    """One scripted launch result for `PlannedLauncher`."""

    pid: int
    returncode: int | None
    block_exit: bool = False


class PlannedLauncher(PortForwardLauncher):
    """Returns scripted sessions per target name, built from the incoming plan."""

    def __init__(self, launches_by_name: dict[str, list[FakeLaunch]]) -> None:
        self._by_name = {
            name: list(launches) for name, launches in launches_by_name.items()
        }

    async def launch(self, plan) -> PortForwardSession:
        launch = self._by_name[plan.target.name].pop(0)
        return FakeSession(
            make_snapshot(
                kind=plan.target.kind,
                namespace=plan.target.namespace,
                name=plan.target.name,
                remote_port=plan.remote_port,
                local_port=plan.local_port,
                pid=launch.pid,
                returncode=launch.returncode,
            ),
            block_exit=launch.block_exit,
        )


class RecordingSleep:
    """Async no-op replacement for `asyncio.sleep` that records its delays."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class ScriptedPortChecker:
    """Returns scripted `is_port_free` results, then stays free."""

    def __init__(self, results: Iterable[bool] = ()) -> None:
        self._results = list(results)
        self._index = 0
        self.calls = 0

    def __call__(self, port: int) -> bool:
        self.calls += 1
        if self._index < len(self._results):
            result = self._results[self._index]
            self._index += 1
            return result
        return True


class _InMemoryRepository:
    def __init__(self, items: list) -> None:
        self._items = items

    def list(self, namespace: str | None = None) -> list:
        if namespace is None:
            return self._items
        return [x for x in self._items if x.metadata.namespace == namespace]

    def get(self, name: str, namespace: str | None = None):
        return next(
            (
                x
                for x in self._items
                if x.metadata.name == name
                and (namespace is None or x.metadata.namespace == namespace)
            ),
            None,
        )


def build_services() -> list[Service]:
    """Two services in the shared test namespace."""
    return [
        Service(
            metadata=ServiceMetadata(name="svc-foo", namespace=NAMESPACE),
            spec=ServiceSpec(ports=[ServicePortModel(port=30, protocol="TCP")]),
        ),
        Service(
            metadata=ServiceMetadata(name="svc-bar", namespace=NAMESPACE),
            spec=ServiceSpec(ports=[ServicePortModel(port=40, protocol="TCP")]),
        ),
    ]


def make_pod(
    name: str,
    namespace: str = NAMESPACE,
    container_ports: list[list[int]] | None = None,
) -> Pod:
    """Build a Pod; each inner list is one container's declared container ports."""
    containers = [[]] if container_ports is None else container_ports
    return Pod(
        metadata=PodMetadata(name=name, namespace=namespace),
        spec=PodSpec(
            containers=[
                PodContainer(ports=[PodContainerPort(container_port=p) for p in ports])
                for ports in containers
            ]
        ),
    )


def build_pods() -> list[Pod]:
    """Two pods in the shared test namespace, each with one container port."""
    return [
        make_pod("pod-foo", container_ports=[[50]]),
        make_pod("pod-bar", container_ports=[[60]]),
    ]


def make_deployment(
    name: str,
    namespace: str = NAMESPACE,
    container_ports: list[list[int]] | None = None,
) -> Deployment:
    """Build a Deployment; each inner list is one container's declared container ports."""
    containers = [[]] if container_ports is None else container_ports
    return Deployment(
        metadata=DeploymentMetadata(name=name, namespace=namespace),
        spec=DeploymentSpec(
            template=Template(
                spec=TemplateSpec(
                    containers=[
                        Container(
                            ports=[ContainerPort(container_port=p) for p in ports]
                        )
                        for ports in containers
                    ]
                )
            )
        ),
    )


def build_deployments() -> list[Deployment]:
    """Two deployments in the shared test namespace, each with one container port."""
    return [
        make_deployment("deploy-foo", container_ports=[[70]]),
        make_deployment("deploy-bar", container_ports=[[80]]),
    ]


def make_fake_api(
    services: list[Service] | None = None,
    pods: list[Pod] | None = None,
    deployments: list[Deployment] | None = None,
) -> KubeGateway:
    """An in-memory KubeGateway backed by the given (or default) services/pods/deployments."""
    services = build_services() if services is None else services
    pods = build_pods() if pods is None else pods
    deployments = build_deployments() if deployments is None else deployments
    namespace = Namespace(metadata=NamespaceMetadata(name=NAMESPACE))
    return cast(
        KubeGateway,
        SimpleNamespace(
            namespace=_InMemoryRepository([namespace]),
            service=_InMemoryRepository(services),
            pod=_InMemoryRepository(pods),
            deployment=_InMemoryRepository(deployments),
            current_config=ResolvedKubeConfig(context="test", namespace=NAMESPACE),
        ),
    )


def _name_from_remote(remote_cell: str) -> str:
    """Extract the bare target name from a ``kind/name:remote_port`` cell."""
    return remote_cell.split("/", 1)[1].rsplit(":", 1)[0]


def rendered_rows_by_name(
    display: PortForwardLiveDisplay,
) -> dict[str, tuple[str, ...]]:
    """Render the status table and key each row's cells by target name.

    Order-independent: supervisor tasks emit STARTED concurrently, so row order
    is not deterministic across runs.
    """
    table = display._table.render()
    columns = [list(col.cells) for col in table.columns]
    rows = [tuple(str(cell) for cell in row) for row in zip(*columns, strict=True)]
    return {_name_from_remote(row[COL_REMOTE]): row for row in rows}
