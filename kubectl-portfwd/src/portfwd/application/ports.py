from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.domain.models import ServicePortForwardPlan


class PortForwardRunner(ABC):
    """Execute port forwarding."""

    @abstractmethod
    def stream(
        self, plans: list[ServicePortForwardPlan]
    ) -> AsyncIterator[PortForwardEvent]:
        """Start port-forwards from `plans` and yield lifecycle events until all exit."""
        raise NotImplementedError
