from __future__ import annotations

import asyncio
import logging
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
from portfwd.kube import get_current_context
from portfwd.runner import (
    _fetch_services_for_namespaces,
    fetch_namespaces,
    fetch_running_forwards,
    manage_port_forwards,
    resolve_services,
)
from portfwd.ui.display import console
from portfwd.ui.prompts import (
    SpecialGroups,
    select_group_name,
    select_namespaces,
    select_services,
)

logger = logging.getLogger(__name__)

app = typer.Typer()


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
    selected = resolve_services(group_obj.services)
    asyncio.run(manage_port_forwards(selected, cfg.ports, context))


def __run_services(service: list[str], cfg: PortFwdConfig, context: str | None) -> None:
    qualnames = [QualifiedName.from_string(s) for s in service]
    selected = resolve_services(qualnames)
    asyncio.run(manage_port_forwards(selected, cfg.ports, context))


def __run_interactive(cfg: PortFwdConfig, context: str | None) -> None:
    all_namespaces, current_namespace = fetch_namespaces()
    selected_namespaces = select_namespaces(all_namespaces, current_namespace)
    available = _fetch_services_for_namespaces(selected_namespaces)
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
