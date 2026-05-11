from __future__ import annotations

import asyncio
import logging
import signal
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import questionary
import typer
from prompt_toolkit.styles import Style
from questionary.constants import DEFAULT_QUESTION_PREFIX
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from portfwd.config import DEFAULT_CONFIG_PATH, ServiceConfig, load_config
from portfwd.kube import (
    KubernetesService,
    PortForwardProcess,
    RunningPortForward,
    find_running_port_forwards,
    get_available_namespaces,
    get_current_context,
    get_services,
    start_port_forward,
)
from portfwd.utils import ensure_port

logger = logging.getLogger(__name__)

app = typer.Typer()
console = Console(stderr=True)


QMARK_COLOR = "#61afef"
ANSWER_COLOR = "#98c379"
POINTER_COLOR = "#61afef"
SELECTED_COLOR = "#98c379"
SEPARATOR_COLOR = "#4b5263"
INSTRUCTION_COLOR = "#4b5263"
DISABLED_COLOR = "#4b5263"

STYLE = Style(
    [
        ("qmark", f"fg:{QMARK_COLOR} bold"),
        ("question", "bold"),
        ("answer", f"fg:{ANSWER_COLOR} bold"),
        ("pointer", f"fg:{POINTER_COLOR} bold"),
        ("highlighted", f"fg:{POINTER_COLOR} bold"),
        ("selected", f"fg:{SELECTED_COLOR}"),
        ("separator", f"fg:{SEPARATOR_COLOR}"),
        ("instruction", f"fg:{INSTRUCTION_COLOR} italic"),
        ("text", ""),
        ("disabled", f"fg:{DISABLED_COLOR} italic"),
    ]
)


def ensure_local_ports(
    services: list[KubernetesService],
    service_configs: list[ServiceConfig],
    namespace: str,
) -> list[tuple[KubernetesService, int]]:
    """Map each service to its assigned local port using config preferences,
    falling back to any free port.
    """
    preferred = {
        (entry.name, entry.remote_port): entry.local_port
        for entry in service_configs
        if entry.namespace == namespace
    }
    result = []
    for svc in services:
        preferred_port = preferred.get((svc.name, svc.port))
        port = ensure_port(preferred_port)
        if preferred_port and port != preferred_port:
            logger.warning(
                "Preferred port %d for %s:%d is not available. Using %d instead.",
                preferred_port,
                svc.name,
                svc.port,
                port,
            )
        result.append((svc, port))
    return result


async def watch_processes(
    processes: list[PortForwardProcess],
    statuses: dict[str, str],
    stop_event: asyncio.Event,
    on_exit: Callable[[], None] = lambda: None,
) -> None:
    """Watch started port-forward processes and update statuses when they exit."""

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


def make_table(
    processes: list[PortForwardProcess],
    statuses: dict[str, str],
    namespace: str,
    context: str | None,
) -> Table:
    """Build the Rich status table for the currently running port-forwards."""
    context_str = f" [dim]({context})[/dim]" if context else ""
    table = Table(
        title=f"[bold]Port Forwards[/bold] — [cyan]{namespace}[/cyan]{context_str}",
        caption="[dim]Press [bold]Ctrl+C[/bold] to stop[/dim]",
        border_style="bright_black",
        show_lines=False,
    )
    table.add_column("Service", style="bold", no_wrap=True)
    table.add_column("Remote", style="cyan", justify="right")
    table.add_column("Local", style="cyan", justify="right")
    table.add_column("PID", style="dim", justify="right")
    table.add_column("Status")
    for fwd in processes:
        key = f"{fwd.service_name}:{fwd.remote_port}"
        raw = statuses.get(key, "live")
        if raw == "live":
            status = "[green]● live[/green]"
        elif raw == "stopped":
            status = "[yellow]■ stopped[/yellow]"
        else:
            status = f"[red]✗ {raw}[/red]"
        table.add_row(
            fwd.service_name,
            f":{fwd.remote_port}",
            f"localhost:{fwd.local_port}",
            str(fwd.process.pid),
            status,
        )
    return table


async def run_port_forwards(
    namespace: str,
    services: list[KubernetesService],
    service_configs: list[ServiceConfig],
    context: str | None,
) -> None:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    processes: list[PortForwardProcess] = []
    statuses: dict[str, str] = {}

    for service, port in ensure_local_ports(services, service_configs, namespace):
        process = await start_port_forward(namespace, service.name, port, service.port)
        processes.append(process)
        statuses[f"{service.name}:{service.port}"] = "live"

    if not processes:
        return

    with Live(
        renderable=make_table(processes, statuses, namespace, context),
        console=console,
        refresh_per_second=1,
    ) as live:

        def refresh() -> None:
            live.update(make_table(processes, statuses, namespace, context))

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


def __get_title(service: KubernetesService) -> str:
    return f"{service.name}  :{service.port}  {service.protocol}"


def __get_key(service: KubernetesService) -> tuple[str, int]:
    return (service.name, service.port)


def build_service_choices(
    available_services: list[KubernetesService],
    running_port_forwards: list[RunningPortForward],
) -> list[questionary.Choice]:
    """Build the questionary choice list for service selection,
    marking already-forwarded services as disabled.
    """
    ports = {(r.name, r.remote_port): r.local_port for r in running_port_forwards}

    choices: list[questionary.Choice] = []

    inactive = [svc for svc in available_services if __get_key(svc) not in ports]
    for svc in inactive:
        title = __get_title(svc)
        choices.append(questionary.Choice(title=title, value=svc))

    active = [svc for svc in available_services if __get_key(svc) in ports]
    for svc in active:
        title = __get_title(svc)
        disabled = f"already forwarded → localhost:{ports[__get_key(svc)]}"
        choices.append(questionary.Choice(title=title, value=svc, disabled=disabled))

    return sorted(choices, key=lambda c: str(c.title))


def select_services(
    available_services: list[KubernetesService],
    running_port_forwards: list[RunningPortForward],
) -> list[KubernetesService]:
    """Interactively prompt the user to select services to port-forward."""
    choices = build_service_choices(available_services, running_port_forwards)
    selected: list[KubernetesService] = questionary.checkbox(
        "Select services to forward:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
        style=STYLE,
    ).ask()
    return selected


def select_namespace(default: str | None, available_namespaces: list[str]) -> str:
    default = default if default in available_namespaces else None

    selected = questionary.select(
        "Select a namespace:",
        choices=available_namespaces,
        use_search_filter=True,
        use_jk_keys=False,
        style=STYLE,
        default=default,
    ).ask()
    if not selected:
        raise typer.Exit(code=0)
    return selected


def __print_error(e: subprocess.CalledProcessError, msg: str) -> None:
    stderr = (e.stderr or "").strip()
    logger.error("Command %s failed [%s]: %s", " ".join(e.cmd), e.returncode, stderr)
    console.print(
        Panel(
            f"[red]{stderr or 'no output'}[/red]",
            title=f"[bold red]{msg}[/bold red]",
            border_style="red",
            expand=False,
        )
    )


def __setup_logging(verbose: int) -> None:
    logging_verbosity = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = logging_verbosity[min(verbose, len(logging_verbosity) - 1)]
    logging.getLogger("kpf").setLevel(level)


@app.callback(invoke_without_command=True)
def port_forward(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            envvar="KPF_CONFIG",
            help=f"Path to TOML config file. Defaults to {DEFAULT_CONFIG_PATH}.",
        ),
    ] = None,
    namespace: Annotated[
        str | None,
        typer.Option(
            "--namespace",
            "-n",
            help="Kubernetes namespace to use "
            "(interactively selected if not provided).",
        ),
    ] = None,
    service: Annotated[
        list[str] | None,
        typer.Option(
            "--service",
            "-s",
            help="Service to forward. Can be specified multiple times. "
            "Skips interactive selection.",
        ),
    ] = None,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Verbose output. Use -vv for more detail.",
        ),
    ] = 0,
) -> None:
    """Interactive kubectl port-forward for Kubernetes services."""

    __setup_logging(verbose)

    context = get_current_context()
    if context:
        console.print(f"[dim]Context:[/dim] [cyan]{context}[/cyan]")

    cfg = load_config(config)

    try:
        with console.status("[bold blue]Fetching namespaces…[/bold blue]"):
            namespaces = get_available_namespaces()
    except subprocess.CalledProcessError as e:
        __print_error(e, "Failed to fetch namespaces using kubectl")
        raise typer.Exit(code=1) from None

    if namespace is None:
        namespace = select_namespace(
            default=cfg.default_namespace, available_namespaces=namespaces
        )
    elif namespace not in namespaces:
        console.print(f"[red]Namespace [bold]{namespace}[/bold] not found.[/red]")
        raise typer.Exit(code=1)
    else:
        console.print(
            f"[bold {QMARK_COLOR}]{DEFAULT_QUESTION_PREFIX}"
            f"[/bold {QMARK_COLOR}] [bold]Select a namespace:[/bold]"
            f" [bold {ANSWER_COLOR}]{namespace}[/bold {ANSWER_COLOR}]"
        )

    try:
        with console.status(
            f"[bold blue]Fetching services in [cyan]{namespace}[/cyan]…[/bold blue]"
        ):
            available_services = get_services(namespace)
    except subprocess.CalledProcessError as e:
        __print_error(
            e, f"Failed to fetch services in namespace {namespace} using kubectl"
        )
        raise typer.Exit(code=1) from None

    if not available_services:
        console.print(
            f"[yellow]No services found in namespace [bold]{namespace}[/bold].[/yellow]"
        )
        raise typer.Exit(code=0)

    if service:
        available_services_map = {s.name: s for s in available_services}
        not_found = {name for name in service if name not in available_services_map}
        if not_found:
            console.print(
                f"[red]Services not found in namespace "
                f"[bold]{namespace}[/bold]: {', '.join(not_found)}[/red]"
            )
            raise typer.Exit(code=1)
        selected = [available_services_map[name] for name in service]
    else:
        running_services = find_running_port_forwards(available_services)
        selected = select_services(
            available_services=available_services,
            running_port_forwards=running_services,
        )
        if not selected:
            console.print("[yellow]No services selected. Exiting.[/yellow]")
            raise typer.Exit(code=0)
    asyncio.run(run_port_forwards(namespace, selected, cfg.ports, context))
