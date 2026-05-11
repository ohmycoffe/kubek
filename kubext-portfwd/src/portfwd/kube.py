from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
from dataclasses import dataclass

import psutil

logger = logging.getLogger(__name__)


@dataclass
class KubernetesService:
    name: str
    port: int
    protocol: str


@dataclass
class RunningPortForward:
    name: str
    remote_port: int
    local_port: int
    pid: int


@dataclass
class PortForwardProcess:
    process: asyncio.subprocess.Process
    local_port: int
    remote_port: int
    service_name: str


def __call_subprocess(cmd: list[str]) -> str:
    logger.debug(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def parse_context(raw: str) -> str:
    """Extract cluster name from a kubectl context string,
    stripping EKS ARN prefix if present.
    """
    assert raw is not None, "Context string is empty"
    context = raw.strip()
    if context.startswith("arn:aws:eks:"):
        return context.split("/")[-1]
    return context


def parse_namespaces(raw: str) -> list[str]:
    """Parse namespace names from `kubectl get namespaces -o json` output."""
    data = json.loads(raw)
    return [el["metadata"]["name"] for el in data["items"]]


def parse_services(raw: str) -> list[KubernetesService]:
    """Parse services from `kubectl get services -o json` output,
    skipping the built-in kubernetes service.
    """
    data = json.loads(raw)
    services: list[KubernetesService] = []
    for svc in data["items"]:
        name = svc["metadata"]["name"]
        if name == "kubernetes":
            continue
        for port in svc["spec"]["ports"]:
            services.append(
                KubernetesService(
                    name=name,
                    port=port["port"],
                    protocol=port["protocol"],
                )
            )
    return sorted(services, key=lambda x: (x.name, x.port))


def get_current_context() -> str:
    """Get the current kubectl context, extracting cluster name from ARN if present."""
    return parse_context(__call_subprocess(["kubectl", "config", "current-context"]))


def get_available_namespaces() -> list[str]:
    """Get the list of available Kubernetes namespaces using kubectl."""
    return parse_namespaces(
        __call_subprocess(["kubectl", "get", "namespaces", "-o", "json"])
    )


def get_services(namespace: str) -> list[KubernetesService]:
    """Get the list of services with their ports in the specified namespace."""
    return parse_services(
        __call_subprocess(["kubectl", "get", "services", "-n", namespace, "-o", "json"])
    )


def find_running_port_forwards(
    services: list[KubernetesService],
) -> list[RunningPortForward]:
    """Find running kubectl port-forward processes that match the given services."""
    known_ports = {(svc.name, svc.port) for svc in services}

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
    )
