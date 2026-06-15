from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from kubek.kube.config import ResolvedKubeConfig

from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.application.ports import (
    PortForwardLauncher,
    PortForwardSession,
)
from portfwd.domain.models import ServicePortForwardPlan

logger = logging.getLogger(__name__)


@dataclass
class PortForwardProcess(PortForwardSession):
    """A running `kubectl port-forward` subprocess and its parameters."""

    process: asyncio.subprocess.Process
    local_port: int
    remote_port: int
    service_name: str
    namespace: str

    def snapshot(self) -> PortForwardProcessSnapshot:
        return PortForwardProcessSnapshot(
            namespace=self.namespace,
            service_name=self.service_name,
            remote_port=self.remote_port,
            local_port=self.local_port,
            pid=self.process.pid,
            returncode=self.process.returncode,
        )

    async def wait(self) -> None:
        await self.process.wait()

    def terminate(self) -> None:
        try:
            self.process.terminate()
        except ProcessLookupError:
            pass


class KubectlPortForwardLauncher(PortForwardLauncher):
    def __init__(self, config: ResolvedKubeConfig) -> None:
        self._config = config

    async def launch(self, plan: ServicePortForwardPlan) -> PortForwardProcess:
        """Spawn a `kubectl port-forward` subprocess and return its handle."""

        namespace = plan.target.namespace
        service = plan.target.name
        local_port = plan.local_port
        remote_port = plan.remote_port
        context = self._config.context
        kubeconfig = self._config.kubeconfig

        args: list[str] = []
        if kubeconfig:
            args += ["--kubeconfig", str(kubeconfig)]
        if context:
            args += ["--context", context]
        cmd = [
            "kubectl",
            *args,
            "port-forward",
            f"svc/{service}",
            f"{local_port}:{remote_port}",
            "--namespace",
            namespace,
        ]
        logger.debug(" ".join(cmd))
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=None,
        )

        logger.debug(
            "Started port forward for %s:%d → localhost:%d [PID: %d]",
            service,
            remote_port,
            local_port,
            process.pid,
        )
        return PortForwardProcess(
            process=process,
            local_port=local_port,
            remote_port=remote_port,
            service_name=service,
            namespace=namespace,
        )
