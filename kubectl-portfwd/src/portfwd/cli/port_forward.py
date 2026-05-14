from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from portfwd.config import (
    DEFAULT_CONFIG_PATH,
    GroupRef,
    PortFwdConfig,
    QualifiedName,
    load_config,
)
from portfwd.kube import (
    KubernetesService,
    get_available_namespaces,
    get_current_context,
    get_current_namespace,
    get_service,
)
from portfwd.runner import (
    fetch_running_forwards,
    fetch_services,
    manage_port_forwards,
)
from portfwd.ui.display import console, print_error
from portfwd.ui.prompts import (
    SpecialGroups,
    select_group_name,
    select_namespaces,
    select_services,
)

logger = logging.getLogger(__name__)

app = typer.Typer()


def __resolve_services(qualnames: list[QualifiedName]) -> list[KubernetesService]:
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


def __fetch_services_for_namespaces(namespaces: list[str]) -> list[KubernetesService]:
    try:
        with console.status("[bold blue]Fetching services…[/bold blue]"):
            return fetch_services(namespaces)
    except subprocess.CalledProcessError as e:
        print_error(e, "Failed to fetch services using kubectl")
        raise typer.Exit(code=1) from None


def __fetch_namespaces() -> tuple[list[str], str | None]:
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


def __setup_logging(verbose: int) -> None:
    logging_verbosity = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = logging_verbosity[min(verbose, len(logging_verbosity) - 1)]
    logging.getLogger("portfwd").setLevel(level)


def __extract_group(group_name: str, available: list[GroupRef]) -> GroupRef | None:
    for group in available:
        if group.name == group_name:
            return group
    return None


def __validate_group(group: str, available: list[GroupRef]) -> None:
    available_groups = {g.name for g in available}
    if not available:
        raise typer.BadParameter("No groups defined in config file.")
    if group not in available_groups:
        raise typer.BadParameter(
            f"--group / -g. Unknown group '{group}' "
            f"(choose from: '{', '.join(sorted(available_groups))}')"
        )


def __run_group(group_name: str, cfg: PortFwdConfig, context: str | None) -> None:
    __validate_group(group_name, cfg.groups)
    group_obj = __extract_group(group_name, cfg.groups)
    assert group_obj is not None
    selected = __resolve_services(group_obj.services)
    asyncio.run(manage_port_forwards(selected, cfg.ports, context))


def __run_services(service: list[str], cfg: PortFwdConfig, context: str | None) -> None:
    qualnames = [QualifiedName.from_string(s) for s in service]
    selected = __resolve_services(qualnames)
    asyncio.run(manage_port_forwards(selected, cfg.ports, context))


def __run_interactive(cfg: PortFwdConfig, context: str | None) -> None:
    all_namespaces, current_namespace = __fetch_namespaces()
    selected_namespaces = select_namespaces(all_namespaces, current_namespace)
    available = __fetch_services_for_namespaces(selected_namespaces)
    if not available:
        console.print("[yellow]No services found.[/yellow]")
        raise typer.Exit(code=0)
    running = fetch_running_forwards(available)
    selected = select_services(available, running)
    asyncio.run(manage_port_forwards(selected, cfg.ports, context))


@app.callback(invoke_without_command=True)
def port_forward(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            envvar="KPF_CONFIG",
            help=f"Path to config file. Defaults to {DEFAULT_CONFIG_PATH}.",
        ),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option(
            "--group",
            "-g",
            help="Run a predefined service group from the config.",
        ),
    ] = None,
    service: Annotated[
        list[str] | None,
        typer.Option(
            "--service",
            "-s",
            help="Service to forward (namespace/name). Can be specified multiple times.",
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

    if group is not None and service is not None:
        raise typer.BadParameter("'--group' and '--service' are mutually exclusive.")

    context = get_current_context()
    if context:
        console.print(f"[dim]Context:[/dim] [cyan]{context}[/cyan]")

    cfg = load_config(config)

    if service is not None:
        __run_services(service, cfg, context)
        return

    if group is not None:
        __run_group(group, cfg, context)
        return

    group_obj = select_group_name(cfg.groups)

    if group_obj is SpecialGroups.CUSTOM:
        __run_interactive(cfg, context)
    else:
        __run_group(group_obj.name, cfg, context)
