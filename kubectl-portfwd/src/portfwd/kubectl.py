from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from os import PathLike

logger = logging.getLogger(__name__)


@dataclass
class PortForwardProcess:
    """A running `kubectl port-forward` subprocess and its parameters."""

    process: asyncio.subprocess.Process
    local_port: int
    remote_port: int
    service_name: str
    namespace: str


async def start_port_forward(
    namespace: str,
    service: str,
    local_port: int,
    remote_port: int,
    context: str | None,
    kubeconfig: str | PathLike | None = None,
) -> PortForwardProcess:
    """Spawn a `kubectl port-forward` subprocess and return its handle."""
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
