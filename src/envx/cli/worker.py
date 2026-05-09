from __future__ import annotations

import enum
import json
import subprocess
from typing import Annotated

import questionary
import typer
from envx.style import STYLE, console, print_error
from envx.kube import (
    call_subprocess,
    extract_envs_from_container,
    get_available_namespaces,
)
from envx.utils import export_as_dotenv, resolve_namespace, setup_logging


def get_available_workers(namespace: str) -> list[str]:
    cmd = ["kubectl", "get", "workflowtemplate", "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    deployments = json.loads(result)
    names = [el["metadata"]["name"] for el in deployments["items"]]
    return names


def get_environment_variables(namespace: str, worker_name: str) -> dict[str, str]:
    cmd = [
        "kubectl",
        "get",
        "workflowtemplate",
        worker_name,
        "-n",
        namespace,
        "-o",
        "json",
    ]
    result = call_subprocess(cmd)
    workflow = json.loads(result)
    templates = workflow["spec"]["templates"]
    envs = {}
    for template in templates:
        if "container" not in template:
            continue
        container = template["container"]
        # Argo allows to provide default values for input parameters, and those parameters can be used in env vars.
        # These parmeters are not visible in the container spec, so we need to extract them from the template inputs.
        fallback_keys = {
            p["name"]: p["default"]
            for p in template.get("inputs", {}).get("parameters", [])
            if "default" in p
        }
        tmp = extract_envs_from_container(
            namespace, container, fallback_keys=fallback_keys
        )
        envs.update(tmp)
    return envs


class ExportFormat(str, enum.Enum):
    ENV = "env"
    JSON = "json"


app = typer.Typer()


@app.callback(invoke_without_command=True)
def get(
    name: Annotated[
        str | None,
        typer.Argument(
            help="Name of the worker to get parameters for. If not provided, you will be prompted to select one."
        ),
    ] = None,
    namespace: Annotated[
        str | None,
        typer.Option(
            envvar="ENVX_NAMESPACE_WORKER",
            help="Kubernetes namespace. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    output: ExportFormat = ExportFormat.ENV,
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True, help="Verbose output. Use -vv for debug."),
    ] = 0,
):
    """
    Get environment variables for a given worker.
    """
    setup_logging(verbose)
    try:
        with console.status("[bold blue]Fetching namespaces…[/bold blue]"):
            namespaces = get_available_namespaces()
    except subprocess.CalledProcessError as e:
        print_error(e, "Failed to fetch namespaces")
        raise typer.Exit(code=1) from None

    namespace = resolve_namespace(namespace, available_namespaces=namespaces)

    try:
        with console.status(f"[bold blue]Fetching workers in {namespace}…[/bold blue]"):
            workers = get_available_workers(namespace=namespace)
    except subprocess.CalledProcessError as e:
        print_error(e, f"Failed to fetch workers in namespace '{namespace}'")
        raise typer.Exit(code=1) from None

    if not name:
        name = questionary.select(
            "Select a worker:",
            choices=workers,
            use_search_filter=True,
            use_jk_keys=False,
            style=STYLE,
        ).ask()
        if not name:
            raise typer.Exit(code=0)

    if name not in workers:
        console.print(
            f"[red]Error:[/red] Worker '{name}' not found in namespace '{namespace}'."
        )
        raise typer.Exit(code=1)

    try:
        with console.status("[bold blue]Fetching environment variables…[/bold blue]"):
            vals = get_environment_variables(namespace=namespace, worker_name=name)
    except subprocess.CalledProcessError as e:
        print_error(e, f"Failed to fetch environment variables for '{name}'")
        raise typer.Exit(code=1) from None

    if output == ExportFormat.JSON:
        formated = json.dumps(vals, sort_keys=True)
    elif output == ExportFormat.ENV:
        formated = export_as_dotenv(vals=vals, name=name)
    print(formated)
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
