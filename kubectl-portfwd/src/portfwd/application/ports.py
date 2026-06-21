from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.contracts.repositories import (
    DaemonSetRepository,
    DeploymentRepository,
    NamespaceRepository,
    PodRepository,
    ServiceRepository,
    StatefulSetRepository,
)
from portfwd.application.port_forwarding.events import OutputLine, PortForwardEvent
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.domain.models import PortForwardPlan


class PortForwardEventStream(ABC):
    """Streams lifecycle events for port-forward plans."""

    @abstractmethod
    def stream(self, plans: list[PortForwardPlan]) -> AsyncIterator[PortForwardEvent]:
        raise NotImplementedError


class KubeGateway(Protocol):
    """Subset of Kubernetes API functionality needed by the application layer."""

    @property
    def current_config(self) -> ResolvedKubeConfig: ...

    @property
    def namespace(self) -> NamespaceRepository: ...

    @property
    def service(self) -> ServiceRepository: ...

    @property
    def pod(self) -> PodRepository: ...

    @property
    def deployment(self) -> DeploymentRepository: ...

    @property
    def statefulset(self) -> StatefulSetRepository: ...

    @property
    def daemonset(self) -> DaemonSetRepository: ...


class PortForwardSession(ABC):
    """A running port-forward session."""

    @abstractmethod
    async def wait(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def terminate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def snapshot(self) -> PortForwardProcessSnapshot:
        raise NotImplementedError

    async def stream_output(self) -> AsyncIterator[OutputLine]:
        """Yield stdout/stderr lines as the subprocess produces them.

        Defaults to no output so sessions that do not capture pipes (e.g. test
        fakes) need not implement it.
        """
        return
        yield  # pragma: no cover - marks this as an (empty) async generator


class PortForwardLauncher(ABC):
    """Launches one port-forward session."""

    @abstractmethod
    async def launch(self, plan: PortForwardPlan) -> PortForwardSession:
        raise NotImplementedError
