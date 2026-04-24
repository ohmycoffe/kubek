from __future__ import annotations

import enum
import json
import logging
from typing import Annotated

import questionary
import typer

from envx.kube import (
    call_subprocess,
    extract_envs_from_container,
    get_available_namespaces,
)
from envx.utils import export_as_dotenv, resolve_namespace

logger = logging.getLogger(__name__)


def get_available_services(namespace: str) -> list[str]:
    cmd = ["kubectl", "get", "deployment", "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    deployments = json.loads(result)
    names = [el["metadata"]["name"] for el in deployments["items"]]
    return names


def get_environment_variables(namespace: str, service_name: str) -> dict[str, str]:
    cmd = ["kubectl", "get", "deployment", service_name, "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    deployment = json.loads(result)
    containers = deployment["spec"]["template"]["spec"]["containers"]
    if len(containers) != 1:
        raise ValueError(f"Expected 1 container, got {len(containers)}")
    container = containers[0]
    envs = extract_envs_from_container(namespace=namespace, container=container)
    return envs


class ExportFormat(str, enum.Enum):
    ENV = "env"
    JSON = "json"


app = typer.Typer()


@app.callback(invoke_without_command=True)
def get(
    service_name: Annotated[
        str | None,
        typer.Argument(
            help="Name of the service to get parameters for. If not provided, you will be prompted to select one."
        ),
    ] = None,
    namespace: Annotated[
        str | None,
        typer.Option(
            envvar="ENVX_NAMESPACE_SERVICE",
            help="Kubernetes namespace. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    output: ExportFormat = ExportFormat.ENV,
):
    """
    Get environment variables for a given service.
    """
    namespaces = get_available_namespaces()
    namespace = resolve_namespace(namespace, available_namespaces=namespaces)
    services = get_available_services(namespace=namespace)
    if not service_name:
        service_name = questionary.select(
            "Select a service:",
            choices=services,
            use_search_filter=True,
            use_jk_keys=False,
        ).ask()
        if not service_name:
            raise typer.Exit(code=0)

    if service_name not in services:
        typer.echo(
            f"Service '{service_name}' not found in namespace '{namespace}'.", err=True
        )
        raise typer.Exit(code=1)

    vals = get_environment_variables(namespace=namespace, service_name=service_name)

    # Format
    if output == ExportFormat.JSON:
        formated = json.dumps(vals, sort_keys=True)
    elif output == ExportFormat.ENV:
        formated = export_as_dotenv(vals=vals, service_name=service_name)
    print(formated)
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
