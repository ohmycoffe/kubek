from __future__ import annotations

import enum
import json
import logging
import os
from typing import Annotated

import questionary
import typer

from envx.kube import (
    call_subprocess,
    extract_envs_from_container,
    get_available_namespaces,
)
from envx.utils import export_as_dotenv, resolve_namespace

logging.basicConfig(level=os.getenv("ENVX_LOGGING_LEVEL", "INFO").upper())

logger = logging.getLogger(__name__)


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
):
    """
    Get environment variables for a given worker.
    """
    namespace = resolve_namespace(
        namespace, available_namespaces=get_available_namespaces()
    )
    workers = get_available_workers(namespace=namespace)
    if not name:
        name = questionary.select(
            "Select a worker:",
            choices=workers,
            use_search_filter=True,
            use_jk_keys=False,
        ).ask()
        if not name:
            raise typer.Exit(code=0)

    if name not in workers:
        typer.echo(f"Worker '{name}' not found in namespace '{namespace}'.", err=True)
        raise typer.Exit(code=1)

    vals = get_environment_variables(namespace=namespace, worker_name=name)

    if output == ExportFormat.JSON:
        formated = json.dumps(vals, sort_keys=True)
    elif output == ExportFormat.ENV:
        formated = export_as_dotenv(vals=vals, name=name)
    print(formated)
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
