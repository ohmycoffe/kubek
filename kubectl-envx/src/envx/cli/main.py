from __future__ import annotations

import enum
import json
import subprocess
from typing import Annotated

import questionary
import typer

from envx.console import console, print_error
from envx.kube import (
    get_available_deployments,
    get_available_namespaces,
    get_available_workflowtemplates,
    get_deployment_envs,
    get_workflowtemplate_envs,
)
from envx.style import COLOR_MUTED, STYLE
from envx.utils import export_as_dotenv, resolve_namespace, setup_logging


class ResourceKind(str, enum.Enum):
    DEPLOYMENT = "deployment"
    WORKFLOWTEMPLATE = "workflowtemplate"


class ExportFormat(str, enum.Enum):
    ENV = "env"
    JSON = "json"


app = typer.Typer()


def select_resource_kind() -> ResourceKind:
    selected = questionary.select(
        "Select a kind:",
        choices=[
            questionary.Choice(
                title="Deployment",
                value=ResourceKind.DEPLOYMENT,
                description="(Kubernetes Deployment)",
            ),
            questionary.Choice(
                title="WorkflowTemplate",
                value=ResourceKind.WORKFLOWTEMPLATE,
                description="(Argo WorkflowTemplate)",
            ),
        ],
        use_jk_keys=False,
        style=STYLE,
    ).ask()
    if not selected:
        raise typer.Exit(code=0)
    return ResourceKind(selected)


@app.callback(invoke_without_command=True)
def get(
    kind: Annotated[
        ResourceKind | None,
        typer.Option(
            help="Kind of resource to get parameters for. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    namespace: Annotated[
        str | None,
        typer.Option(
            envvar="KENVX_NAMESPACE",
            help="Kubernetes namespace. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option(
            help="Name of the resource. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    output: ExportFormat = ExportFormat.ENV,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose", "-v", count=True, help="Verbose output. Use -vv for debug."
        ),
    ] = 0,
):
    """
    Get environment variables for a Kubernetes deployment or Argo WorkflowTemplate.
    """
    setup_logging(verbose)
    if kind is None:
        kind = select_resource_kind()

    try:
        with console.status(f"[italic {COLOR_MUTED}]Fetching available namespaces…[/]"):
            namespaces = get_available_namespaces()
    except subprocess.CalledProcessError as e:
        print_error(e, "Failed to fetch available namespaces")
        raise typer.Exit(code=1) from None

    namespace = resolve_namespace(namespace, available_namespaces=namespaces)

    try:
        with console.status(
            f"[italic {COLOR_MUTED}]Fetching available {kind.value}s in {namespace}…[/]"
        ):
            if kind == ResourceKind.DEPLOYMENT:
                resources = get_available_deployments(namespace=namespace)
            else:
                resources = get_available_workflowtemplates(namespace=namespace)
    except subprocess.CalledProcessError as e:
        print_error(
            e, f"Failed to fetch available {kind.value}s in namespace '{namespace}'"
        )
        raise typer.Exit(code=1) from None
    if not resources:
        console.print(f"[red]Error: no {kind.value}s found in namespace '{namespace}'")
        raise typer.Exit(code=1)

    if not name:
        name = questionary.select(
            f"Select a {kind.value}:",
            choices=resources,
            use_search_filter=True,
            use_jk_keys=False,
            style=STYLE,
        ).ask()
        if not name:
            raise typer.Exit(code=0)

    if name not in resources:
        console.print(
            f"[red]Error:[/red] {kind.value} '{name}' not found in namespace '{namespace}'."
        )
        raise typer.Exit(code=1)

    try:
        with console.status(
            f"[italic {COLOR_MUTED}]Fetching environment variables…[/]"
        ):
            if kind == ResourceKind.DEPLOYMENT:
                vals = get_deployment_envs(namespace=namespace, name=name)
            else:
                vals = get_workflowtemplate_envs(namespace=namespace, name=name)
    except subprocess.CalledProcessError as e:
        print_error(e, f"Failed to fetch environment variables for '{name}'")
        raise typer.Exit(code=1) from None

    if output == ExportFormat.JSON:
        formatted = json.dumps(vals, sort_keys=True)
    elif output == ExportFormat.ENV:
        formatted = export_as_dotenv(vals=vals, name=name)
    print(formatted)
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
