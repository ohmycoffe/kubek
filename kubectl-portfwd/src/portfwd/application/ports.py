from abc import ABC, abstractmethod

from portfwd.domain.models import ServicePortForwardPlan


class PortForwardRunner(ABC):
    """Execute port forwarding"""

    @abstractmethod
    async def run(self, plans: list[ServicePortForwardPlan]) -> None:
        """Given a list of port-forward plans, execute them and manage their lifecycle."""
        raise NotImplementedError
