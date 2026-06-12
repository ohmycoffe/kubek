from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.contracts.repositories import NamespaceRepository, ServiceRepository
from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.domain.models import ServicePortForwardPlan


class PortForwardEventStream(ABC):
    """Streams lifecycle events for port-forward plans."""

    @abstractmethod
    def stream(
        self, plans: list[ServicePortForwardPlan]
    ) -> AsyncIterator[PortForwardEvent]:
        raise NotImplementedError


class KubeGateway(Protocol):
    """Subset of Kubernetes API functionality needed by the application layer."""

    @property
    def current_config(self) -> ResolvedKubeConfig: ...

    @property
    def namespace(self) -> NamespaceRepository: ...

    @property
    def service(self) -> ServiceRepository: ...


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


class PortForwardLauncher(ABC):
    """Launches one port-forward session."""

    @abstractmethod
    async def launch(self, plan: ServicePortForwardPlan) -> PortForwardSession:
        raise NotImplementedError
