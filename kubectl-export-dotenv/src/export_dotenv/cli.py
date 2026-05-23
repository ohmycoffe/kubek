from __future__ import annotations

import enum
import json
from pathlib import Path
from typing import Annotated, Literal

import typer
from click import BadParameter
from kubek.kube import Kind, KubeFacade
from kubek.kube.config import KubeConfig
from kubek.term.output import CLIOutput, create_output

from export_dotenv.kube import (
    get_deployment_envs,
    get_workflowtemplate_envs,
)
from export_dotenv.prompts import ask_for_kind, ask_for_resource
from export_dotenv.utils import export_as_dotenv, setup_logging


class ExportFormat(enum.StrEnum):
    ENV = "env"
    JSON = "json"


app = typer.Typer()


@app.callback(invoke_without_command=True)
def get(
    kind: Annotated[
        Literal[Kind.DEPLOYMENT, Kind.WORKFLOWTEMPLATE] | None,
        typer.Option(
            case_sensitive=False,
            help="Kind of resource to get parameters for. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    context: Annotated[
        str | None,
        typer.Option(
            help="Kubernetes context. If not provided, the current context will be used.",
        ),
    ] = None,
    kubeconfig: Annotated[
        Path | None,
        typer.Option(
            "--kubeconfig",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help="Path to a kubeconfig file (single path). Omit to use kubectl's default.",
        ),
    ] = None,
    namespace: Annotated[
        str | None,
        typer.Option(
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
    out: CLIOutput = create_output(verbosity_count=verbose)

    kubeconfig_str = kubeconfig if kubeconfig else None

    kube_config = KubeConfig(
        context=context,
        namespace=namespace,
        kubeconfig=kubeconfig_str,
    )
    api = KubeFacade.from_config(config=kube_config)

    if kube_config.kubeconfig:
        out.note(
            f"Kubeconfig: {kube_config.kubeconfig}",
            highlight=[str(kube_config.kubeconfig)],
        )

    if kube_config.context:
        out.note(
            f"Context: {kube_config.context}",
            highlight=[str(kube_config.context)],
        )

    if kube_config.namespace:
        out.note(
            f"Namespace: {kube_config.namespace}",
            highlight=[str(kube_config.namespace)],
        )

    kind = kind or ask_for_kind()  # type: ignore

    if not kind:
        raise typer.Exit(code=0)

    try:
        with out.progress(
            f"Fetching available {kind.value}s in {kube_config.namespace}…"
        ):
            if kind == Kind.DEPLOYMENT:
                resources = api.deployment.list()
            else:
                resources = api.workflowtemplate.list()
    except Exception as e:
        out.exception(f"Failed to fetch {kind.value}s: {e}")
        raise typer.Exit(code=1) from None
    if not resources:
        out.problem(f"No {kind.value}s found in namespace '{kube_config.namespace}'")
        raise typer.Exit(code=1)

    available_names = [r.metadata.name for r in resources]
    if not name:
        name = ask_for_resource(resources=available_names, kind=kind)
        if not name:
            raise typer.Exit(code=0)

    if name not in available_names:
        out.problem(
            f"{kind.value} '{name}' not found in namespace '{kube_config.namespace}'"
        )
        raise typer.Exit(code=1)

    try:
        with out.progress("Fetching environment variables…"):
            if kind == Kind.DEPLOYMENT:
                vals = get_deployment_envs(name=name, api=api)
            elif kind == Kind.WORKFLOWTEMPLATE:
                vals = get_workflowtemplate_envs(name=name, api=api)
            else:
                raise BadParameter(f"Unsupported kind: {kind}")
    except Exception as e:
        out.exception(f"Failed to fetch environment variables for '{name}': {e}")
        raise typer.Exit(code=1) from None

    if output == ExportFormat.JSON:
        formatted = json.dumps(vals, sort_keys=True)
    elif output == ExportFormat.ENV:
        formatted = export_as_dotenv(vals=vals, name=name)
    print(formatted)
    raise typer.Exit(code=0)
