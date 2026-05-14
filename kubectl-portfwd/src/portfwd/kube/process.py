from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PortForwardProcess:
    process: asyncio.subprocess.Process
    local_port: int
    remote_port: int
    service_name: str
    namespace: str


@dataclass
class RunningPortForward:
    name: str
    remote_port: int
    local_port: int
    pid: int


def find_running_port_forwards(
    known_ports: set[tuple[str, int]],
) -> list[RunningPortForward]:
    """Find running kubectl port-forward processes matching the given (name, port) pairs.

    Args:
        known_ports: Set of (service_name, remote_port) tuples to match against.

    Returns:
        List of running port-forward processes.
    """
    kubectl_procs = [
        proc
        for proc in psutil.process_iter(["pid", "name", "cmdline"])
        if proc.info["name"] == "kubectl"
    ]

    running: list[RunningPortForward] = []
    for proc in kubectl_procs:
        cmdline = proc.info["cmdline"]
        svc_match = re.search(
            r"(?:svc|service)/(?P<name>[a-zA-Z0-9-]+)", " ".join(cmdline)
        )
        if not svc_match:
            continue
        service_name = svc_match.group("name")

        for arg in cmdline:
            port_match = re.fullmatch(r"(?:(?P<local>\d+):)?(?P<remote>\d+)", arg)
            if not port_match:
                continue
            remote_port = int(port_match.group("remote"))
            local_port = (
                int(port_match.group("local"))
                if port_match.group("local")
                else remote_port
            )
            if (service_name, remote_port) in known_ports:
                running.append(
                    RunningPortForward(
                        name=service_name,
                        remote_port=remote_port,
                        local_port=local_port,
                        pid=proc.info["pid"],
                    )
                )

    return running


async def start_port_forward(
    namespace: str, service: str, local_port: int, remote_port: int
) -> PortForwardProcess:
    """Start a kubectl port-forward process for the specified service and port."""
    cmd = [
        "kubectl",
        "port-forward",
        f"svc/{service}",
        f"{local_port}:{remote_port}",
        "-n",
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
