from __future__ import annotations

import enum
import json
import logging
import os

import typer

from envx.kube import call_subprocess, extract_envs_from_container
from envx.utils import export_as_dotenv

logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO").upper())


logger = logging.getLogger(__name__)


def get_available_workers(namespace: str):
    cmd = ["kubectl", "get", "workflowtemplate", "-n", namespace, "-o", "json"]
    result = call_subprocess(cmd)
    deployments = json.loads(result)
    names = [el["metadata"]["name"] for el in deployments["items"]]
    return names


def get_environment_variables(namespace: str, worker_name: str):
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
        tmp = extract_envs_from_container(namespace, container)
        envs.update(tmp)

    return envs


class ExportFormat(str, enum.Enum):
    ENV = "env"
    JSON = "json"


app = typer.Typer()


@app.command()
def get(
    name: str = typer.Argument(
        help="Name of the worker to get parameters for.",
    ),
    namespace: str = "kube-public",
    output: ExportFormat = ExportFormat.ENV,
):
    """
    Get environment variables for a given worker.
    """
    vals = get_environment_variables(namespace=namespace, worker_name=name)

    # Format
    if output == ExportFormat.JSON:
        formated = json.dumps(vals, sort_keys=True)
    elif output == ExportFormat.ENV:
        formated = export_as_dotenv(vals=vals, service_name=name)
    print(formated)
    raise typer.Exit(code=0)


@app.command(name="list")
def list_workers(
    namespace: str = "kube-public",
):
    """
    List all available workers.
    """
    deployments = get_available_workers(namespace=namespace)
    print("Available workers:\n")
    for el in deployments:
        print(el)
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
