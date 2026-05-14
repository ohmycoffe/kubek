from __future__ import annotations

import asyncio
import itertools
import logging
import signal
import subprocess
from collections.abc import Callable
from typing import TYPE_CHECKING

import typer
from rich.live import Live

from portfwd.kube import (
    find_running_port_forwards,
    get_available_namespaces,
    get_current_namespace,
    get_service,
    get_services,
    start_port_forward,
)
from portfwd.ui.display import console, make_table, print_error
from portfwd.utils import find_free_port, is_port_free

if TYPE_CHECKING:
    from portfwd.config import QualifiedName, ServiceConfig
    from portfwd.kube import KubernetesService, PortForwardProcess, RunningPortForward

logger = logging.getLogger(__name__)


def ensure_local_ports(
    services: list[KubernetesService],
    service_configs: list[ServiceConfig],
) -> list[tuple[KubernetesService, int]]:
    """Map each service to its assigned local port.

    Uses the configured local_port if present and free; hard-fails if the configured
    port is taken. Assigns a random free port when no config mapping exists.
    """
    preferred = {
        (entry.namespace, entry.name, entry.remote_port): entry.local_port
        for entry in service_configs
    }
    result = []
    for svc in services:
        preferred_port = preferred.get((svc.namespace, svc.name, svc.port))
        if preferred_port is not None:
            if not is_port_free(preferred_port):
                console.print(
                    f"[red]Port {preferred_port} configured for {svc.namespace}/{svc.name} "
                    f"is already in use.[/red]"
                )
                raise typer.Exit(code=1)
            result.append((svc, preferred_port))
        else:
            result.append((svc, find_free_port()))
    return result


async def watch_processes(
    processes: list[PortForwardProcess],
    statuses: dict[str, str],
    stop_event: asyncio.Event,
    on_exit: Callable[[], None] = lambda: None,
) -> None:
    async def _watch(process: PortForwardProcess) -> None:
        await process.process.wait()
        if not stop_event.is_set():
            statuses[f"{process.service_name}:{process.remote_port}"] = (
                f"died (exit {process.process.returncode})"
            )
            on_exit()

    async with asyncio.TaskGroup() as tg:
        for proc in processes:
            tg.create_task(_watch(proc))


async def manage_port_forwards(
    services: list[KubernetesService],
    service_configs: list[ServiceConfig],
    context: str | None,
) -> None:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    processes: list[PortForwardProcess] = []
    statuses: dict[str, str] = {}

    for service, port in ensure_local_ports(services, service_configs):
        process = await start_port_forward(
            service.namespace, service.name, port, service.port
        )
        processes.append(process)
        statuses[f"{service.name}:{service.port}"] = "live"

    if not processes:
        return

    with Live(
        renderable=make_table(processes, statuses, context),
        console=console,
        refresh_per_second=1,
    ) as live:

        def refresh() -> None:
            live.update(make_table(processes, statuses, context))

        def cleanup() -> None:
            stop_event.set()
            for proc in processes:
                try:
                    proc.process.terminate()
                    statuses[f"{proc.service_name}:{proc.remote_port}"] = "stopped"
                except ProcessLookupError:
                    pass
            refresh()

        loop.add_signal_handler(signal.SIGINT, cleanup)
        loop.add_signal_handler(signal.SIGTERM, cleanup)

        await watch_processes(
            processes=processes,
            statuses=statuses,
            stop_event=stop_event,
            on_exit=refresh,
        )


def resolve_services(qualnames: list[QualifiedName]) -> list[KubernetesService]:
    """Look up each service by exact name in its namespace.

    Hard-fails on missing services or kubectl errors, distinguishing the two cases.
    """
    result: list[KubernetesService] = []
    not_found: list[str] = []
    try:
        with console.status("[bold blue]Fetching services…[/bold blue]"):
            for q in qualnames:
                svc = get_service(q.namespace, q.name)
                if svc is None:
                    not_found.append(str(q))
                else:
                    result.append(svc)
    except subprocess.CalledProcessError as e:
        print_error(e, "Failed to fetch service using kubectl")
        raise typer.Exit(code=1) from None
    if not_found:
        console.print(f"[red]Services not found: {', '.join(not_found)}[/red]")
        raise typer.Exit(code=1)
    return result


def fetch_services(namespaces: list[str]) -> list[KubernetesService]:
    return list(itertools.chain.from_iterable(get_services(ns) for ns in namespaces))


def _fetch_services_for_namespaces(namespaces: list[str]) -> list[KubernetesService]:
    try:
        with console.status("[bold blue]Fetching services…[/bold blue]"):
            return fetch_services(namespaces)
    except subprocess.CalledProcessError as e:
        print_error(e, "Failed to fetch services using kubectl")
        raise typer.Exit(code=1) from None


def fetch_namespaces() -> tuple[list[str], str | None]:
    """Fetch all namespaces and current namespace.

    Returns tuple of (all_namespaces, current_namespace).
    """
    try:
        with console.status("[bold blue]Fetching namespaces…[/bold blue]"):
            all_namespaces = get_available_namespaces()
            current = get_current_namespace()
            return all_namespaces, current
    except subprocess.CalledProcessError as e:
        print_error(e, "Failed to fetch namespaces using kubectl")
        raise typer.Exit(code=1) from None


def fetch_running_forwards(
    services: list[KubernetesService],
) -> list[RunningPortForward]:
    """Fetch running port-forward processes for the given services."""
    known_ports = {(svc.name, svc.port) for svc in services}
    return find_running_port_forwards(known_ports)
